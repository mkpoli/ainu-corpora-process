from utils.data.pos import combined_pos


def get_pos(word: str, default: list[str] = []) -> list[str]:
    return combined_pos.get(word, default)
