"""Công thức Elo thuần: nhận hai rating và kết quả trận, trả delta của hai người.

Module không sửa DB. Service execute.py cộng các delta vào User.rating và
lưu chúng vào RoomPlayer.elo_change trong transaction kết thúc trận Ranked.
"""

K_FACTOR = 32  # Hệ số quyết định mức độ tăng/giảm rating sau một trận.
MIN_RATING = 100  # Rating sau trận không được thấp hơn mức này.


def calculate_elo(rating_a: int, rating_b: int, score_a: float) -> tuple[int, int]:
    """Trả (delta_a, delta_b), không trả rating mới.

    score_a: 1 nếu A thắng, 0 nếu A thua, 0.5 nếu hòa; điểm B là 1 - score_a.
    Ví dụ A/B cùng 1200 điểm, A thắng: kết quả (16, -16).
    Hàm tính được trường hợp hòa; luồng Submit hiện chỉ gọi khi có người thắng.
    """
    if score_a not in (0, 0.5, 1):
        raise ValueError("Điểm thực tế phải là 0, 0.5 hoặc 1")
    # E_A là kỳ vọng thắng của A. Hai rating bằng nhau -> E_A = 0.5.
    # A thắng đối thủ mạnh hơn thì phần (S_A - E_A) lớn hơn, nhận nhiều điểm hơn.
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    delta_a = round(K_FACTOR * (score_a - expected_a))
    # Tính B với S_B = 1 - S_A và E_B = 1 - E_A; round làm tròn về số nguyên.
    delta_b = round(K_FACTOR * ((1 - score_a) - (1 - expected_a)))
    # Áp sàn vào rating MỚI rồi trừ rating cũ để ra delta thực tế.
    # Ví dụ rating 105, delta lý thuyết -16 -> rating mới 100, delta thực tế -5.
    # Vì có sàn, tổng hai delta có thể không bằng 0.
    return (
        max(MIN_RATING, rating_a + delta_a) - rating_a,
        max(MIN_RATING, rating_b + delta_b) - rating_b,
    )
