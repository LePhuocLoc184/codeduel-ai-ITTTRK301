from app.schemas.users import RankBadge
from app.models.room_players import RoomPlayer

# =============================== XÁC ĐỊNH RANK CHO USER ===============================

def rank_badge_for(rating: int) -> RankBadge:
    if rating >= 1700:
        return RankBadge.DIAMOND
    if rating >= 1500:
        return RankBadge.GOLD
    if rating >= 1300:
        return RankBadge.SILVER
    return RankBadge.BRONZE
# =============================== END REGION ===============================

# =============================== TÍNH TỈ LỆ WIN ===============================

def win_rate_for(wins: int, rated_games: int) -> float:
    if rated_games <= 0:
        return 0.0
    return round((wins / rated_games) * 100, 2)
# =============================== END REGION ===============================


def _is_decisive_win(player: RoomPlayer, mates: list[RoomPlayer]) -> bool:
    if any(mate.elo_change != 0 for mate in mates):
        return player.elo_change > 0
    if len(mates) < 2:
        return False
    top_score = max(mate.score for mate in mates)
    leaders = [mate for mate in mates if mate.score == top_score]
    return len(leaders) == 1 and leaders[0].user_id == player.user_id