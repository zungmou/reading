import traceback
import asyncio
import argparse
import edge_tts


async def main():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="输入文件")
    parser.add_argument("-m", "--model", help="语音模型", default="zh-CN-YunjianNeural")
    parser.add_argument("-o", "--output", help="输出文件", default="__output__.mp3")

    try:
        args = parser.parse_args()

        def get_input_text():
            with open(args.file, "r", encoding="utf-8") as f:
                return f.read()

        def get_input_rate():
            return f"+0%"

        def get_input_volume():
            return f"+0%"

        tts = edge_tts.Communicate(
            text=get_input_text(),
            voice=args.model,
            rate=get_input_rate(),
            volume=get_input_volume(),
        )

        await tts.save(args.output)
    except SystemExit:
        pass
    except:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
