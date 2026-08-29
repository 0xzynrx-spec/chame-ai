"""主导障碍识别 — 读 Student 三列取最大，默认 concept"""


def get_dominant_barrier(student) -> str:
    """读取三列障碍占比取主导障碍；三列全 0（无画像）时默认 concept"""
    dist = {
        "concept": student.barrier_concept_rate or 0.0,
        "reading": student.barrier_reading_rate or 0.0,
        "expression": student.barrier_expression_rate or 0.0,
    }
    if dist["concept"] == dist["reading"] == dist["expression"] == 0.0:
        return "concept"
    return max(dist, key=dist.get)
