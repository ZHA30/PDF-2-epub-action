import os  
from pathlib import Path  
from pdf_craft import PDFPageExtractor
from pdf_craft import OCRLevel  
from pdf_craft.analysers.ocr import generate_ocr_pages  
from pdf_craft.analysers.reporter import Reporter  

# filepath: /home/AppData/pdf-craft/Pdf2epub.py
import warnings
warnings.filterwarnings("ignore")

def ocr_stage_one(pdf_path: str, output_dir: str, model_dir: str, device: str = "cpu"):  

    # 设置路径  
    pdf_path = Path(pdf_path)  
    output_dir = Path(output_dir)  
    ocr_path = output_dir / "ocr"  
    assets_path = output_dir / "assets"  
      
    # 创建输出目录  
    for path in (ocr_path, assets_path):  
        path.mkdir(parents=True, exist_ok=True)  
      
    # 配置 OCR 提取器  
    extractor = PDFPageExtractor(  
        device=device,  
        model_dir_path=model_dir,
        #ocr_level=OCRLevel.OncePerLayout,
    )  
      
    def report_step_callback(step):  
        print(f"当前步骤: {step.name}")  
    
    def report_progress_callback(completed, total):  
        if total:  
            print(f"进度: {completed}/{total}")  
        else:  
            print(f"已完成: {completed}")  
    
    # 配置报告器  
    reporter = Reporter(  
        report_step=report_step_callback,  
        report_progress=report_progress_callback  
    )
      
    # 执行 OCR 第一阶段  
    generate_ocr_pages(  
        extractor=extractor,  
        reporter=reporter,  
        pdf_path=pdf_path,  
        ocr_path=ocr_path,  
        assets_path=assets_path,  
    )  
      
    print("OCR 第一阶段完成!")  
    print(f"OCR 数据保存在: {ocr_path}")  
    print(f"资源文件保存在: {assets_path}")  
      
    return {  
        "ocr_path": str(ocr_path),  
        "assets_path": str(assets_path),  
        "status": "completed"  
    }  
  
if __name__ == "__main__":  
    import argparse  
      
    parser = argparse.ArgumentParser(description="OCR 第一阶段 - EPUB 生成准备")  
    parser.add_argument("pdf_path", help="输入 PDF 文件路径")  
    parser.add_argument("output_dir", help="输出目录路径")  
    parser.add_argument("model_dir", help="AI 模型目录路径")  
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"],   
                       help="使用的设备 (默认: cpu)")  
      
    args = parser.parse_args()  
      
    try:  
        result = ocr_stage_one(  
            pdf_path=args.pdf_path,  
            output_dir=args.output_dir,  
            model_dir=args.model_dir,  
            device=args.device  
        )  
        print(f"结果: {result}")  
    except Exception as e:  
        print(f"错误: {e}")  
        exit(1)