from utils.sakhalin import extrapolate_sakhalin_from_hokkaido


def test_extrapolate_sakhalin_from_hokkaido():
    assert extrapolate_sakhalin_from_hokkaido("sat") == "sah"
    assert extrapolate_sakhalin_from_hokkaido("pirka") == "pirika"
    assert extrapolate_sakhalin_from_hokkaido("ikra") == "isra"
    assert extrapolate_sakhalin_from_hokkaido("kim") == "kin"
