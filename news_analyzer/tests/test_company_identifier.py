# tests/test_company_identifier.py
from news_analyzer.company_identifier import CompanyIdentifier

def test_company_detection():
    ci = CompanyIdentifier()
    assert set(ci.identify_companies("삼성전자와 LG전자 협력")) >= {"삼성전자","LG전자"}
    res = ci.identify_companies("현대자동차 신차")
    assert "현대자동차" in res and "현대차" in res
    assert ci.identify_companies("일반 텍스트") == []
