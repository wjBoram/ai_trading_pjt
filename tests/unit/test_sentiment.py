"""data.sentiment 모듈 단위 테스트"""

from data.sentiment import aggregate_sentiment, score_text_sentiment


class TestScoreTextSentiment:
    def test_positive_text(self):
        score = score_text_sentiment("실적 호조로 주가 급등, 목표가 상향 조정")
        assert score is not None
        assert score > 0

    def test_negative_text(self):
        score = score_text_sentiment("실적 악화로 주가 급락, 적자 우려 확산")
        assert score is not None
        assert score < 0

    def test_neutral_text_with_no_keywords(self):
        assert score_text_sentiment("오늘 회의가 진행되었다") == 0.0

    def test_empty_text_returns_none(self):
        assert score_text_sentiment("") is None
        assert score_text_sentiment(None) is None

    def test_score_bounded_between_minus_one_and_one(self):
        score = score_text_sentiment("상승 " * 50)
        assert score == 1.0


class TestAggregateSentiment:
    def test_averages_valid_scores(self):
        assert aggregate_sentiment([0.5, -0.5, 1.0]) == round((0.5 - 0.5 + 1.0) / 3, 4)

    def test_ignores_none_values(self):
        assert aggregate_sentiment([0.4, None, 0.6]) == 0.5

    def test_all_none_returns_none(self):
        assert aggregate_sentiment([None, None]) is None

    def test_empty_list_returns_none(self):
        assert aggregate_sentiment([]) is None
