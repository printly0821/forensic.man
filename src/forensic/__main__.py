"""forensic.man CLI entry point."""

from click import group


@group()
def main():
    """forensic.man - 녹취자료 분석 도구"""
    pass


if __name__ == "__main__":
    main()
