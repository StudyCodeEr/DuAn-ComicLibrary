-- Schema v2 cua mangalib.
--
-- Sua gi so voi schema v1 (core/database.py):
--   * v1 luu manga.path va cover_path TUYET DOI -> phai co smart_path_resolve de
--     do lai khi thu muc di chuyen. v2 luu slug + ten file tuong doi (quy tac R5).
--   * v1 khong co bang chapter/page -> reader phai os.listdir moi lan va khong
--     resume duoc. v2 co ca hai, kem status de biet chuong nao tai thieu.
--   * v1 sap chuong theo ten thu muc -> chuong 10 dung truoc chuong 2. v2 co
--     chapter.number REAL.
--   * v1 khong co tac gia. v2 co bang author + manga_author, phan biet tac gia
--     voi hoa si, va origin='manual' de tai lai khong xoa thu nguoi dung sua tay.
--   * v1 khong co vi tri doc. v2 co bang progress -> dong bo PC <-> dien thoai.
--   * v1 khong luu trang thai/loi tai. v2 co bang job, co cot error.
--   * v1 tim kiem LIKE '%...%' that bai voi dau. v2 co title_sort/name_sort khong dau.
--   * v1 chi co page_count -> khong doi chieu duoc. v2 co ca expected_page_count,
--     lech nhau nghia la chuong 'partial'.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source (
    key       TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    base_url  TEXT NOT NULL,
    rule_file TEXT,
    enabled   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS manga (
    id           INTEGER PRIMARY KEY,
    -- slug = ten thu muc. Duong dan that luon la paths.library_dir()/slug,
    -- nen di chuyen ca thu vien chi can doi data_root.
    slug         TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    title_sort   TEXT NOT NULL,
    source_key   TEXT REFERENCES source(key) ON DELETE SET NULL,
    source_url   TEXT UNIQUE,
    cover_file   TEXT,
    description  TEXT,
    added_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT,
    last_read_at TEXT,
    -- Xoa mem: file anh van nam nguyen tren dia, nen hoan tac duoc.
    deleted_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_manga_sort  ON manga(title_sort);
CREATE INDEX IF NOT EXISTS idx_manga_added ON manga(added_at DESC);

CREATE TABLE IF NOT EXISTS chapter (
    id                  INTEGER PRIMARY KEY,
    manga_id            INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    number              REAL,
    title               TEXT NOT NULL,
    dir_name            TEXT NOT NULL,
    source_url          TEXT,
    page_count          INTEGER NOT NULL DEFAULT 0,
    expected_page_count INTEGER,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'partial', 'complete', 'failed')),
    downloaded_at       TEXT,
    deleted_at          TEXT,
    -- Thu tu do nguoi dung tu keo. NULL = xep theo `number` nhu mac dinh.
    sort_index          INTEGER,
    UNIQUE (manga_id, dir_name)
);

CREATE INDEX IF NOT EXISTS idx_chapter_order ON chapter(manga_id, number, dir_name);

CREATE TABLE IF NOT EXISTS page (
    chapter_id INTEGER NOT NULL REFERENCES chapter(id) ON DELETE CASCADE,
    idx        INTEGER NOT NULL,
    file_name  TEXT NOT NULL,
    source_url TEXT,
    width      INTEGER,
    height     INTEGER,
    byte_size  INTEGER,
    PRIMARY KEY (chapter_id, idx)
);

CREATE TABLE IF NOT EXISTS tag (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS manga_tag (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tag(id)   ON DELETE CASCADE,
    origin   TEXT NOT NULL DEFAULT 'scraped'
             CHECK (origin IN ('scraped', 'manual')),
    PRIMARY KEY (manga_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_mangatag_tag ON manga_tag(tag_id);

CREATE TABLE IF NOT EXISTS author (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name_sort TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_author_sort ON author(name_sort);

CREATE TABLE IF NOT EXISTS manga_author (
    manga_id  INTEGER NOT NULL REFERENCES manga(id)  ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES author(id) ON DELETE CASCADE,
    role      TEXT NOT NULL DEFAULT 'author'
              CHECK (role IN ('author', 'artist')),
    origin    TEXT NOT NULL DEFAULT 'scraped'
              CHECK (origin IN ('scraped', 'manual')),
    PRIMARY KEY (manga_id, author_id, role)
);

CREATE INDEX IF NOT EXISTS idx_mangaauthor_author ON manga_author(author_id);

CREATE TABLE IF NOT EXISTS progress (
    manga_id   INTEGER PRIMARY KEY REFERENCES manga(id)   ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL    REFERENCES chapter(id) ON DELETE CASCADE,
    page_idx   INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS job (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    manga_id    INTEGER REFERENCES manga(id) ON DELETE SET NULL,
    state       TEXT NOT NULL
                CHECK (state IN ('queued', 'running', 'done', 'failed',
                                 'cancelled', 'needs_login')),
    phase       TEXT,
    done        INTEGER NOT NULL DEFAULT 0,
    total       INTEGER NOT NULL DEFAULT 0,
    -- Loi duoc LUU lai, khong bi nuot nhu 17 cho `except: pass` cua ban cu.
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_state ON job(state, created_at DESC);
