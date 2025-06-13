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
import contextlib

STEP_NAMES = {
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

def llm_stage_two(
    ocr_output_dir: str,
    final_output_dir: str,
    llm_config: dict,
    correction_mode: str = "NO",
    window_tokens: int = 2000,
    threads_count: int = 1
):

    ocr_output_dir = Path(ocr_output_dir).resolve()
    final_output_dir = Path(final_output_dir).resolve()
    analysing_dir = (final_output_dir / "temp").resolve()

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

    llm = LLM(**llm_config)
    window_tokens = parse_window_tokens(window_tokens)
    threads = MultiThreads(threads_count)

    # 进度报告
    def report_step(step: AnalysingStep):
        step_name = STEP_NAMES.get(step, step.name)
        print(f"Step: {step_name}")

    bar = None
    def report_progress(completed_count: int, max_count: int | None):
        nonlocal bar
        if bar is None:
            bar = tqdm(total=max_count, desc="处理中")
        bar.n = completed_count
        bar.refresh()

    reporter = Reporter(
        report_step=report_step,
        report_progress=report_progress,
    )

    print(f"开始 LLM 分析阶段")
    print(f"OCR 数据路径: {ocr_path}")
    print(f"最终输出路径: {final_output_dir}")

    try:
        with contextlib.ExitStack() as stack:
            if bar:
                stack.enter_context(bar)
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

    except Exception as e:
        print(f"分析过程中发生异常: {e}")
        raise
    finally:
        if bar is not None:
            bar.close()

    return {
        "output_path": str(final_output_dir),
        "meta_path": str(meta_path),
        "chapter_path": str(chapter_output_path),
        "status": "completed"
    }

if __name__ == "__main__":
    ocr_output_dir = os.environ.get("OCR_OUTPUT_DIR")
    final_output_dir = os.environ.get("FINAL_OUTPUT_DIR")
    if not ocr_output_dir or not final_output_dir:
        raise ValueError("OCR_OUTPUT_DIR 和 FINAL_OUTPUT_DIR 环境变量不能为空")
    correction_mode = os.environ.get("CORRECTION_MODE", "NO")
    window_tokens = int(os.environ.get("WINDOW_TOKENS", 2000))
    threads_count = int(os.environ.get("THREADS", 4))

    llm_config = {
        "key": os.environ.get("LLM_KEY"),
        "url": os.environ.get("LLM_URL", "https://api.deepseek.com"),
        "model": os.environ.get("LLM_MODEL", "deepseek-chat"),
        "token_encoding": os.environ.get("LLM_TOKEN_ENCODING", "o200k_base"),
        "temperature": float(os.environ.get("LLM_TEMPERATURE", 0.3)),
        "top_p": float(os.environ.get("LLM_TOP_P", 0.8)),
    }