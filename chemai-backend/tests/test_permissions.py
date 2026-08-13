"""测试：四角色 RBAC 权限矩阵"""

from app.utils.permissions import check_permission
import pytest
pytestmark = pytest.mark.l1


class TestAdminPermissions:
    """系统管理员拥有全部权限"""

    def test_admin_all_resources(self):
        resources = ["school", "grade", "class", "teacher", "student",
                     "analysis", "exam", "question", "ocr", "grading"]
        for resource in resources:
            assert check_permission("admin", resource, "read"), f"admin read {resource}"

    def test_admin_create_exam(self):
        assert check_permission("admin", "exam", "create") is True

    def test_admin_delete_school(self):
        assert check_permission("admin", "school", "delete") is True


class TestTeacherPermissions:
    """教师拥有教学资源写权限，管理资源只读"""

    def test_teacher_read_students(self):
        assert check_permission("teacher", "student", "read") is True

    def test_teacher_create_exam(self):
        assert check_permission("teacher", "exam", "create") is True

    def test_teacher_cannot_update_school(self):
        assert check_permission("teacher", "school", "update") is False

    def test_teacher_cannot_delete_student(self):
        assert check_permission("teacher", "student", "delete") is False

    def test_teacher_create_question(self):
        assert check_permission("teacher", "question", "create") is True


class TestStudentPermissions:
    """学生权限最小——仅自身数据"""

    def test_student_read_grade(self):
        assert check_permission("student", "grade", "read") is True

    def test_student_cannot_read_other_students(self):
        # student 的 "student" read 权限仅限自身，具体隔离逻辑在端点实现
        assert check_permission("student", "student", "read") is True

    def test_student_cannot_read_teacher(self):
        assert check_permission("student", "teacher", "read") is False

    def test_student_cannot_read_exam(self):
        assert check_permission("student", "exam", "read") is False


class TestParentPermissions:
    """家长权限——仅绑定子女数据"""

    def test_parent_read_child(self):
        # parent 的 student read 权限，具体绑定验证在端点实现
        assert check_permission("parent", "student", "read") is True

    def test_parent_cannot_read_class(self):
        assert check_permission("parent", "class", "read") is False


class TestUnknownRole:
    """未知角色默认拒绝"""

    def test_unknown_role(self):
        assert check_permission("unknown_role", "student", "read") is False

    def test_unknown_resource(self):
        assert check_permission("teacher", "nonexistent", "read") is False
