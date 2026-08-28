"""
핫딜 소스 레지스트리.

각 소스 모듈은 fetch() -> list[deal dict] 하나만 노출한다.
새 소스를 추가하려면: 모듈을 만들고 아래 _SOURCE_MODULES 에 한 줄 등록하면 끝.

deal dict 스키마는 common.py 상단 주석 참고.
"""

import importlib

# 키(레지스트리 이름) -> 모듈 이름.
# 등록 순서 = dedupe() 우선순위 (먼저 온 소스의 항목을 남긴다).
# 뽐뿌/루리웹/클리앙을 알구몬·텔레그램보다 앞에 둬서, 겹치는 딜은
# 원본 커뮤니티 링크가 살아남도록 한다.
_SOURCE_MODULES = {
    "ppomppu": "ppomppu",
    "ruliweb": "ruliweb",
    "clien": "clien",
    "algumon": "algumon",
    "telegram": "telegram",
    "coupang": "coupang",
    "aliexpress": "aliexpress",
}


def _load(module_name):
    mod = importlib.import_module(f".{module_name}", __name__)
    return mod.fetch


class _LazyRegistry:
    """이름으로 접근할 때 해당 소스 모듈을 import 하고 fetch 함수를 돌려준다."""

    def get(self, name):
        module_name = _SOURCE_MODULES.get(name)
        if module_name is None:
            return None
        return _load(module_name)

    def __contains__(self, name):
        return name in _SOURCE_MODULES

    def __iter__(self):
        return iter(_SOURCE_MODULES)


SOURCE_REGISTRY = _LazyRegistry()

__all__ = ["SOURCE_REGISTRY"]
