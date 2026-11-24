"""Tên file, slug, số chương, tác giả — toàn hàm thuần, chạy trong millisecond."""

from __future__ import annotations

import pytest

from mangalib import naming


class TestCleanFilename:
    def test_removes_forbidden_chars(self):
        assert naming.clean_filename('a<b>c:d"e/f\\g|h?i*j') == "a-b-c-d-e-f-g-h-i-j"

    def test_strips_control_chars(self):
        """WinError 123 của bản cũ: ký tự xuống dòng trong tên thư mục."""
        assert naming.clean_filename("Tên\ntruyện\tdài") == "Tên truyện dài"

    def test_trailing_dot_and_space_removed(self):
        assert naming.clean_filename("Chương 1. ") == "Chương 1"

    @pytest.mark.parametrize("reserved", ["CON", "NUL", "COM1", "lpt3", "con.txt"])
    def test_reserved_device_names(self, reserved):
        """Windows không cho đặt tên này, kể cả có phần mở rộng."""
        assert naming.clean_filename(reserved).startswith("_")

    def test_unicode_preserved(self):
        assert naming.clean_filename("Thiên Đường Không Hồi Kết") == "Thiên Đường Không Hồi Kết"

    def test_truncates_long_names(self):
        assert len(naming.clean_filename("A" * 300)) <= naming.MAX_NAME_LENGTH

    def test_empty_gets_fallback(self):
        assert naming.clean_filename("   ") == "Khong-ten"

    def test_unique_name_adds_suffix(self):
        assert naming.unique_name("truyen", {"truyen", "truyen-2"}) == "truyen-3"


class TestSortKey:
    def test_removes_diacritics(self):
        assert naming.sort_key("Thể loại") == "the loai"

    def test_handles_d_with_stroke(self):
        """NFD không tách `đ`, phải xử lý riêng."""
        assert naming.sort_key("Đường") == "duong"

    def test_collapses_whitespace(self):
        assert naming.sort_key("  Trần   Đăng  Khoa ") == "tran dang khoa"

    def test_slugify(self):
        assert naming.slugify("Thiên Đường Không Hồi Kết!") == "thien-duong-khong-hoi-ket"


class TestStripSiteSuffix:
    SUFFIXES = ("Việt Hentai - Hentai Vietsub HD", "Việt Hentai")

    def test_strips_real_seo_tail(self):
        """Trường hợp thật trên đĩa."""
        title = "Thiên Đường Không Hồi Kết - Việt Hentai - Hentai Vietsub HD"
        assert naming.strip_site_suffix(title, self.SUFFIXES) == "Thiên Đường Không Hồi Kết"

    def test_leaves_clean_title_alone(self):
        assert naming.strip_site_suffix("Một Tên Sạch", self.SUFFIXES) == "Một Tên Sạch"

    def test_never_returns_empty(self):
        assert naming.strip_site_suffix("Việt Hentai", self.SUFFIXES) == "Việt Hentai"


class TestChapterNumber:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Chương 10", 10.0),
            ("Chương 1", 1.0),
            ("Chapter 9.5", 9.5),
            ("Chap 3", 3.0),
            ("ch.7", 7.0),
            ("Tập 2 - Chương 3", 3.0),
            ("Chương 12,5", 12.5),
            ("Oneshot", None),
            ("Nội dung trực tiếp", None),
            ("", None),
        ],
    )
    def test_parse_variants(self, title, expected):
        assert naming.parse_chapter_number(title) == expected

    def test_sort_numeric_not_lexicographic(self):
        """Bản cũ sắp theo tên nên chương 10 đứng trước chương 2."""
        titles = ["Chương 10", "Chương 2", "Chương 1", "Chương 21"]
        ordered = sorted(titles, key=lambda t: naming.parse_chapter_number(t) or 0)
        assert ordered == ["Chương 1", "Chương 2", "Chương 10", "Chương 21"]

    def test_does_not_mistake_digit_inside_name(self):
        """`main.py:245` đảo thứ tự dựa vào việc tên chứa ký tự "1"."""
        assert naming.parse_chapter_number("Chương 10") == 10.0

    def test_dir_name_is_zero_padded(self):
        assert naming.chapter_dir_name(10, "Chương 10") == "0010 - Chương 10"
        assert naming.chapter_dir_name(1, "Chương 1") == "0001 - Chương 1"

    def test_dir_name_keeps_fraction(self):
        assert naming.chapter_dir_name(9.5, "Chương 9.5").startswith("0009.5 - ")

    def test_dir_name_without_number(self):
        assert naming.chapter_dir_name(None, "Oneshot") == "Oneshot"

    def test_zero_padded_dirs_sort_correctly(self):
        names = [naming.chapter_dir_name(n, f"Chương {n}") for n in (1, 2, 10, 21)]
        assert sorted(names) == names


class TestPeople:
    def test_strips_label_prefix(self):
        assert naming.normalize_person_name("Tác giả: Asahina Yoshitosi") == "Asahina Yoshitosi"
        assert naming.normalize_person_name("Họa sĩ - Ai Đó") == "Ai Đó"

    def test_collapses_whitespace(self):
        assert naming.normalize_person_name("  Asahina   Yoshitosi ") == "Asahina Yoshitosi"

    @pytest.mark.parametrize(
        "value",
        ["Đang cập nhật", "N/A", "-", "unknown", "Chưa rõ", "", "   ", "Tác giả"],
    )
    def test_rejects_placeholder_values(self, value):
        """Placeholder không được lưu thành tác giả."""
        assert naming.is_placeholder_person(value)

    def test_real_name_is_not_placeholder(self):
        assert not naming.is_placeholder_person("Asahina Yoshitosi")

    def test_splits_multiple_authors(self):
        assert naming.split_people("A, B & C / D") == ["A", "B", "C", "D"]

    def test_split_drops_placeholders_and_duplicates(self):
        assert naming.split_people("Asahina, Đang cập nhật, asahina") == ["Asahina"]

    def test_missing_author_is_empty_list_not_fake_value(self):
        assert naming.split_people("Đang cập nhật") == []
        assert naming.split_people("") == []

    def test_name_sort_finds_unaccented_query(self):
        assert naming.sort_key("Trần Đăng Khoa") == "tran dang khoa"
