"""ダミーの問い合わせメモ・議事録を生成するスクリプト。

外部通信・外部ライブラリには依存せず、固定文面の組み合わせのみで合成データを生成する。
生成されるデータに実在の個人情報は含まれない。
"""
from pathlib import Path

MEMO_TXT_PATH = Path(__file__).parent / "sample_inquiry.txt"
MEMO_MD_PATH = Path(__file__).parent / "sample_meeting_notes.md"


def generate_memo_text() -> str:
    """プレーンテキストのダミー問い合わせメモを1件生成する。"""
    return (
        "【問い合わせ内容】\n"
        "田中太郎様より、商品Aについてお問い合わせがありました。\n"
        "折り返し先: 090-1234-5678\n"
        "住所: 東京都渋谷区1-2-3\n"
        "担当の鈴木一郎が対応予定です。\n"
    )


def generate_meeting_notes_markdown() -> str:
    """Markdown形式のダミー議事録を1件生成する。"""
    return (
        "# 定例会議メモ\n\n"
        "- 参加者: 佐藤花子様、鈴木一郎（担当）\n"
        "- 佐藤花子様の連絡先は080-2345-6789です。\n"
        "- 次回訪問先住所: 大阪府大阪市北区4-5-6\n"
    )


def main() -> None:
    """サンプルの.txt/.mdファイルを生成する。"""
    MEMO_TXT_PATH.write_text(generate_memo_text(), encoding="utf-8")
    print(f"生成しました: {MEMO_TXT_PATH}")

    MEMO_MD_PATH.write_text(generate_meeting_notes_markdown(), encoding="utf-8")
    print(f"生成しました: {MEMO_MD_PATH}")


if __name__ == "__main__":
    main()
