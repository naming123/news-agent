# company_identifier.py
from __future__ import annotations
from typing import List, Dict, Set

class CompanyIdentifier:
    """
    Identify major Korean company names in text.
    - Case-insensitive (for romanized names); for Korean, we do substring matching.
    - Deduplicate results.
    - Synonym groups: if one alias is found, we can return canonical names + key aliases.
    """
    def __init__(self, companies: List[str] | None = None):
        # 최소 20개 기업/별칭 포함 (일부는 동의어/축약 포함)
        base_list = companies or [
            "삼성전자","삼성","LG전자","LG화학","현대자동차","현대차","기아","SK하이닉스","SK텔레콤","SK이노베이션",
            "네이버","카카오","포스코","한화","롯데케미칼","KT","신한은행","KB금융","하나금융","CJ제일제당",
            "셀트리온","두산","현대모비스","LG디스플레이","삼성SDI","삼성바이오로직스","현대중공업","팬오션","카카오뱅크"
        ]
        # 동의어/브랜드 묶음 정의 (간단 예시)
        self.synonym_groups = [
            {"삼성전자","삼성"},
            {"현대자동차","현대차"},
            {"LG전자","LG"},
            {"LG화학","LG"},
            {"SK하이닉스","SK하닉","SK"},
            {"네이버","NAVER"},
            {"카카오","KAKAO"},
        ]
        self.company_set: Set[str] = set(base_list)

    def _expand_with_synonyms(self, found: Set[str]) -> Set[str]:
        # 그룹 내 매칭되면 그 그룹의 대표/별칭도 결과에 포함
        expanded = set(found)
        for group in self.synonym_groups:
            if group & found:
                expanded |= group
        return expanded & self.company_set if expanded else expanded

    def identify_companies(self, text: str) -> List[str]:
        if not isinstance(text, str) or len(text) == 0:
            return []
        t = text.lower()
        found = set()
        for name in self.company_set:
            if any(part in t for part in [name.lower()]):
                if name in text:
                    found.add(name)
                else:
                    # 영문 별칭 매칭 대비
                    if name.lower() in t:
                        found.add(name)
        # 동의어 확장 (요구 테스트 "현대자동차 신차" -> ['현대자동차','현대차'] 지원)
        found = self._expand_with_synonyms(found)
        # 출력은 입력에서 등장한 순서를 최대한 보존하려 노력 (간단 구현)
        ordered = []
        for token in text.split():
            token_clean = token.strip(' ,.;:()[]{}"\n\t')
            for name in self.company_set:
                if name == token_clean and name in found and name not in ordered:
                    ordered.append(name)
        # 누락된 것 덧붙이기
        for name in sorted(found):
            if name not in ordered:
                ordered.append(name)
        return ordered


