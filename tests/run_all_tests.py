import asyncio
import subprocess
import sys
from pathlib import Path


async def run_test_file(test_file: str):
    """运行单个测试文件"""
    print(f'\n{"="*60}')
    print(f'运行测试: {test_file}')
    print(f'{"="*60}\n')
    
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(test_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent
        )
        
        stdout, stderr = await asyncio.gather(
            process.communicate(),
            return_exceptions=False
        )
        
        if stdout:
            print(stdout.decode('utf-8', errors='ignore'))
        if stderr:
            print(stderr.decode('utf-8', errors='ignore'))
        
        return process.returncode == 0
    except Exception as e:
        print(f'运行测试失败: {e}')
        return False


async def main():
    """主测试运行器"""
    tests_dir = Path(__file__).parent
    
    test_files = [
        'test_story_plan.py',
        'test_quality_evaluation.py',
        'test_character_and_novel.py'
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            success = await run_test_file(test_path)
            results[test_file] = '通过' if success else '失败'
        else:
            print(f'测试文件不存在: {test_file}')
            results[test_file] = '不存在'
    
    print(f'\n{"="*60}')
    print('测试结果汇总')
    print(f'{"="*60}')
    for test_file, result in results.items():
        print(f'{test_file}: {result}')
    print(f'{"="*60}')


if __name__ == "__main__":
    asyncio.run(main())
