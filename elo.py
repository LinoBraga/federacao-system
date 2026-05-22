# elo.py

K = 25


def expected(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_rating(rating, score, expected_score):
    return rating + K * (score - expected_score)