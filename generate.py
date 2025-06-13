import os    
from pathlib import Path    
from pdf_craft import generate_epub_file, TableRender, LaTeXRender    
    
def epub_stage_three(    
    analysis_output_dir: str,    
    epub_file_path: str,    
    language: str = "zh",    
    table_render_mode: str = "HTML",    
    latex_render_mode: str = "MATHML"    
):    
 
    analysis_output_dir = Path(analysis_output_dir).resolve()    
    epub_file_path = Path(epub_file_path).resolve()    
        
    # 验证必需的输入目录结构    
    required_files = [    
        analysis_output_dir / "meta.json",    
        analysis_output_dir / "chapters"    
    ]    
        
    for required_file in required_files:    
        if not required_file.exists():    
            raise FileNotFoundError(f"必需文件不存在: {required_file}")    
      
    # 检查可选的 index.json 文件  
    index_file = analysis_output_dir / "index.json"  
    has_index = index_file.exists()  
      
    if not has_index:  
        print("警告: 未找到 index.json 文件，EPUB 将不包含目录结构")  
        
    # 配置渲染选项    
    table_render = TableRender.HTML if table_render_mode == "HTML" else TableRender.CLIPPING    
        
    if latex_render_mode == "MATHML":    
        latex_render = LaTeXRender.MATHML    
    elif latex_render_mode == "SVG":    
        latex_render = LaTeXRender.SVG    
    else:    
        latex_render = LaTeXRender.CLIPPING    
        
    print(f"开始 EPUB 生成阶段")    
    print(f"分析结果目录: {analysis_output_dir}")    
    print(f"EPUB 输出路径: {epub_file_path}")    
    print(f"语言: {language}")    
    print(f"表格渲染模式: {table_render_mode}")    
    print(f"公式渲染模式: {latex_render_mode}")    
    print(f"包含目录结构: {'是' if has_index else '否'}")  
        
    # 确保输出目录存在    
    epub_file_path.parent.mkdir(parents=True, exist_ok=True)    
      
    try:  
        # 生成 EPUB 文件    
        generate_epub_file(    
            from_dir_path=analysis_output_dir,    
            epub_file_path=epub_file_path,    
            lan=language,    
            table_render=table_render,    
            latex_render=latex_render,    
        )    
            
        print("EPUB 生成完成!")    
        print(f"EPUB 文件保存在: {epub_file_path}")    
          
        # 验证生成的文件  
        if not epub_file_path.exists():  
            raise FileNotFoundError(f"EPUB 文件生成失败: {epub_file_path}")  
              
        file_size = epub_file_path.stat().st_size  
        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")  
          
        return {    
            "epub_path": str(epub_file_path),    
            "file_size": file_size,  
            "has_index": has_index,  
            "status": "completed"    
        }  
          
    except Exception as e:  
        print(f"EPUB 生成过程中发生错误: {e}")  
        raise  
    
if __name__ == "__main__":    
    import argparse    
        
    parser = argparse.ArgumentParser(description="EPUB 第三阶段 - 生成电子书")    
    parser.add_argument("analysis_output_dir", help="LLM 分析结果目录")    
    parser.add_argument("epub_file_path", help="输出 EPUB 文件路径")    
    parser.add_argument("--language", default="zh", choices=["zh", "en"],    
                       help="电子书语言 (默认: zh)")    
    parser.add_argument("--table-render", default="HTML", choices=["HTML", "CLIPPING"],    
                       help="表格渲染模式 (默认: HTML)")    
    parser.add_argument("--latex-render", default="MATHML", choices=["MATHML", "SVG", "CLIPPING"],    
                       help="公式渲染模式 (默认: MATHML)")    
        
    args = parser.parse_args()    
        
    try:    
        result = epub_stage_three(    
            analysis_output_dir=args.analysis_output_dir,    
            epub_file_path=args.epub_file_path,    
            language=args.language,    
            table_render_mode=args.table_render,    
            latex_render_mode=args.latex_render    
        )    
        print(f"结果: {result}")    
    except Exception as e:    
        print(f"错误: {e}")    
        exit(1)