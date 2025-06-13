import os    
from pathlib import Path    
from tqdm import tqdm  
from pdf_craft import LLM    
from pdf_craft.analysers.sequence import extract_sequences    
from pdf_craft.analysers.correction import correct, Level as CorrectionLevel    
from pdf_craft.analysers.meta import extract_meta    
from pdf_craft.analysers.contents import extract_contents    
from pdf_craft.analysers.chapter import generate_chapters    
from pdf_craft.analysers.reference import generate_chapters_with_footnotes    
from pdf_craft.analysers.output import output    
from pdf_craft.analysers.reporter import Reporter, AnalysingStep    
from pdf_craft.analysers.window import parse_window_tokens, LLMWindowTokens    
from pdf_craft.analysers.utils import MultiThreads    
from pdf_craft.analysers.types import CorrectionMode    
    
def llm_stage_two(    
    ocr_output_dir: str,    
    final_output_dir: str,    
    llm_config: dict,    
    correction_mode: str = "NO",    
    window_tokens: int = 2000,    
    threads_count: int = 1    
):    
   
    # 转换为绝对路径以避免路径错误  
    ocr_output_dir = Path(ocr_output_dir).resolve()    
    final_output_dir = Path(final_output_dir).resolve()    
    analysing_dir = final_output_dir / "temp"     
    analysing_dir = analysing_dir.resolve()  # 确保分析目录也是绝对路径  
        
    # OCR 第一阶段的输出路径    
    ocr_path = ocr_output_dir / "ocr"    
    assets_path = ocr_output_dir / "assets"    
        
    # LLM 分析的工作路径    
    sequence_path = analysing_dir / "sequence"    
    correction_path = analysing_dir / "correction"    
    contents_path = analysing_dir / "contents"    
    chapter_path = analysing_dir / "chapter"    
    reference_path = analysing_dir / "reference"    
        
    # 创建必要目录    
    for path in [analysing_dir, sequence_path, correction_path, contents_path, chapter_path, reference_path, final_output_dir]:    
        path.mkdir(parents=True, exist_ok=True)    
        
    # 配置 LLM    
    llm = LLM(**llm_config)    
        
    # 配置其他组件    
    window_tokens = parse_window_tokens(window_tokens)    
    threads = MultiThreads(threads_count)    
      
    # 进度报告变量  
    bar: tqdm | None = None  
    count: int = 0  
      
    # 定义进度报告回调函数  
    def report_step(step: AnalysingStep):  
        nonlocal bar, count  
        bar = None  
        count = 0  
        # 自定义中文步骤名称映射  
        step_names = {  
            AnalysingStep.EXTRACT_SEQUENCE: "提取文本序列",  
            AnalysingStep.VERIFY_TEXT_PARAGRAPH: "验证文本段落",   
            AnalysingStep.VERIFY_FOOTNOTE_PARAGRAPH: "验证脚注段落",  
            AnalysingStep.CORRECT_TEXT: "校正文本",  
            AnalysingStep.CORRECT_FOOTNOTE: "校正脚注",  
            AnalysingStep.EXTRACT_META: "提取元数据",  
            AnalysingStep.COLLECT_CONTENTS: "提取目录结构",  
            AnalysingStep.MAPPING_CONTENTS: "映射目录内容",  
            AnalysingStep.GENERATE_FOOTNOTES: "生成脚注",  
            AnalysingStep.OUTPUT: "生成最终输出"  
        }  
        step_name = step_names.get(step, step.name)  
        print(f"Step: {step_name}")  
  
    def report_progress(completed_count: int, max_count: int | None):  
        nonlocal bar, count  
        if bar is None:  
            bar = tqdm(total=max_count, desc="处理中")  
        bar.update(completed_count - count)  
        count = completed_count  
      
    # 创建带进度报告的 Reporter  
    reporter = Reporter(  
        report_step=report_step,  
        report_progress=report_progress,  
    )  
        
    print(f"开始 LLM 分析阶段")    
    print(f"OCR 数据路径: {ocr_path}")    
    print(f"最终输出路径: {final_output_dir}")    
      
    try:  

        extract_sequences(    
            llm=llm,    
            reporter=reporter,    
            threads=threads,    
            workspace_path=sequence_path,    
            ocr_path=ocr_path,    
            max_request_data_tokens=window_tokens.max_request_data_tokens,    
            max_paragraph_tokens=window_tokens.max_verify_paragraph_tokens,    
            max_paragraphs=window_tokens.max_verify_paragraphs_count,    
        )    
        sequence_output_path = sequence_path / "output"    
            
        if correction_mode != "NO":    
            level = CorrectionLevel.Single if correction_mode == "ONCE" else CorrectionLevel.Multiple    
            sequence_output_path = correct(    
                llm=llm,    
                reporter=reporter,    
                threads=threads,    
                level=level,    
                workspace_path=correction_path,    
                text_path=sequence_output_path / "text",    
                footnote_path=sequence_output_path / "footnote",    
                max_data_tokens=window_tokens.max_request_data_tokens,    
            )    
            
        meta_path = extract_meta(    
            llm=llm,    
            workspace_path=analysing_dir / "meta",    
            sequence_path=sequence_output_path / "text",    
            max_request_tokens=window_tokens.max_request_data_tokens,    
        )    
            
        contents = extract_contents(    
            llm=llm,    
            reporter=reporter,    
            workspace_path=contents_path,    
            sequence_path=sequence_output_path / "text",    
            max_data_tokens=window_tokens.max_request_data_tokens,    
        )    
            
        chapter_output_path, contents = generate_chapters(    
            llm=llm,    
            reporter=reporter,    
            threads=threads,    
            contents=contents,    
            sequence_path=sequence_output_path / "text",    
            workspace_path=chapter_path,    
            max_request_tokens=window_tokens.max_request_data_tokens,    
        )    
            
        footnote_sequence_path = sequence_output_path / "footnote"    
        if footnote_sequence_path.exists():    
            chapter_output_path = generate_chapters_with_footnotes(    
                reporter=reporter,    
                chapter_path=chapter_output_path,    
                footnote_sequence_path=footnote_sequence_path,    
                workspace_path=reference_path,    
            )    
            
        output(    
            contents=contents,    
            output_path=final_output_dir,    
            meta_path=meta_path,    
            chapter_output_path=chapter_output_path,    
            assets_path=assets_path,    
        )    
            
        print("LLM 分析阶段完成!")    
        print(f"分析结果保存在: {final_output_dir}")    
          
    finally:  
        # 确保进度条正确关闭  
        if bar is not None:  
            bar.close()  
        
    return {    
        "output_path": str(final_output_dir),    
        "meta_path": str(meta_path),    
        "chapter_path": str(chapter_output_path),    
        "status": "completed"    
    }    
    
if __name__ == "__main__":    
    import argparse    
    import json    
        
    parser = argparse.ArgumentParser(description="LLM 第二阶段 - 智能分析")    
    parser.add_argument("ocr_output_dir", help="OCR 第一阶段的输出目录")    
    parser.add_argument("final_output_dir", help="最终输出目录")    
    parser.add_argument("--llm-config", required=True, help="LLM 配置 JSON 文件路径")    
    parser.add_argument("--correction-mode", default="NO", choices=["NO", "ONCE", "DETAILED"],    
                       help="文本校正模式 (默认: NO)")    
    parser.add_argument("--window-tokens", type=int, default=2000,    
                       help="LLM 请求窗口大小 (默认: 2000)")    
    parser.add_argument("--threads", type=int, default=1,    
                       help="并发线程数 (默认: 1)")    
        
    args = parser.parse_args()    
        
    # 读取 LLM 配置    
    with open(args.llm_config, 'r', encoding='utf-8') as f:    
        llm_config = json.load(f)    
        
    try:    
        result = llm_stage_two(    
            ocr_output_dir=args.ocr_output_dir,    
            final_output_dir=args.final_output_dir,    
            llm_config=llm_config,    
            correction_mode=args.correction_mode,    
            window_tokens=args.window_tokens,    
            threads_count=args.threads    
        )    
        print(f"结果: {result}")    
    except Exception as e:    
        print(f"错误: {e}")    
        exit(1)