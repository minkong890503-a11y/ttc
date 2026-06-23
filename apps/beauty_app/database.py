import os, sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'beauty_app.db')


def get_db_connection():
    """SQLite 연결을 생성합니다."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    """웹앱에서 사용하는 모든 테이블을 생성하고 초기 관리자 계정을 준비합니다."""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('staff','manager','owner')),
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS customer_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('결제','시술','환불','기타')),
        customer_type TEXT CHECK(customer_type IN ('신규','구환')),
        gender TEXT CHECK(gender IN ('남','여')),
        customer_name TEXT NOT NULL,
        visit_time TEXT,
        card_amount INTEGER DEFAULT 0,
        cash_amount INTEGER DEFAULT 0,
        transfer_amount INTEGER DEFAULT 0,
        credit_amount INTEGER DEFAULT 0,
        memo TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cosmetic_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL UNIQUE,
        stock_quantity INTEGER DEFAULT 0,
        unit_price INTEGER DEFAULT 0,
        total_amount INTEGER DEFAULT 0,
        memo TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cosmetic_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        staff_name TEXT NOT NULL,
        customer_name TEXT,
        product_name TEXT DEFAULT '',
        quantity INTEGER DEFAULT 0,
        card_amount INTEGER DEFAULT 0,
        cash_amount INTEGER DEFAULT 0,
        transfer_amount INTEGER DEFAULT 0,
        credit_amount INTEGER DEFAULT 0,
        memo TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cosmetic_sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        unit_price INTEGER DEFAULT 0,
        line_total INTEGER DEFAULT 0,
        FOREIGN KEY (sale_id) REFERENCES cosmetic_sales(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES cosmetic_inventory(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        card_amount INTEGER DEFAULT 0,
        cash_amount INTEGER DEFAULT 0,
        memo TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cash_closing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL UNIQUE,
        prev_cash INTEGER DEFAULT 0,
        cash_sales INTEGER DEFAULT 0,
        cash_expense INTEGER DEFAULT 0,
        expected_cash INTEGER DEFAULT 0,
        actual_cash INTEGER,
        difference INTEGER,
        confirmed_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS daily_closing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        version INTEGER DEFAULT 1,
        total_card_sales INTEGER DEFAULT 0,
        total_cash_sales INTEGER DEFAULT 0,
        total_transfer_sales INTEGER DEFAULT 0,
        total_credit_used INTEGER DEFAULT 0,
        total_treatment_sales INTEGER DEFAULT 0,
        total_cosmetic_sales INTEGER DEFAULT 0,
        total_sales INTEGER DEFAULT 0,
        total_card_expense INTEGER DEFAULT 0,
        total_cash_expense INTEGER DEFAULT 0,
        total_expense INTEGER DEFAULT 0,
        net_profit INTEGER DEFAULT 0,
        expected_cash INTEGER DEFAULT 0,
        actual_cash INTEGER DEFAULT 0,
        cash_difference INTEGER DEFAULT 0,
        status TEXT DEFAULT '미결산',
        saved_by TEXT,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # 결산분석용 일별 요약 테이블입니다. 원천 입력 데이터가 저장될 때마다 재계산되어 최신값을 유지합니다.
    c.execute("""CREATE TABLE IF NOT EXISTS daily_closing_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL UNIQUE,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        weekday TEXT NOT NULL,
        male_count INTEGER DEFAULT 0,
        female_count INTEGER DEFAULT 0,
        new_customer_count INTEGER DEFAULT 0,
        returning_customer_count INTEGER DEFAULT 0,
        total_visit_count INTEGER DEFAULT 0,
        new_customer_sales INTEGER DEFAULT 0,
        returning_customer_sales INTEGER DEFAULT 0,
        card_treatment_sales INTEGER DEFAULT 0,
        cash_treatment_sales INTEGER DEFAULT 0,
        transfer_treatment_sales INTEGER DEFAULT 0,
        total_treatment_sales INTEGER DEFAULT 0,
        card_cosmetic_sales INTEGER DEFAULT 0,
        cash_cosmetic_sales INTEGER DEFAULT 0,
        transfer_cosmetic_sales INTEGER DEFAULT 0,
        total_cosmetic_sales INTEGER DEFAULT 0,
        total_daily_sales INTEGER DEFAULT 0,
        credit_used INTEGER DEFAULT 0,
        card_expense INTEGER DEFAULT 0,
        cash_expense INTEGER DEFAULT 0,
        total_expense INTEGER DEFAULT 0,
        closing_amount INTEGER DEFAULT 0,
        is_workday INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    if not c.execute('SELECT id FROM users WHERE name=?', ('admin',)).fetchone():
        c.execute('INSERT INTO users (name,password,role) VALUES (?,?,?)', ('admin', generate_password_hash(os.environ.get('BEAUTY_APP_ADMIN_PASSWORD', 'change-me')), 'owner'))

    conn.commit()
    conn.close()
    recalculate_all_summaries()
    print('DB 초기화 완료: beauty_app.db')
    print('초기 관리자 계정: admin / BEAUTY_APP_ADMIN_PASSWORD')


def _safe_date(value):
    """YYYY-MM-DD 날짜 문자열인지 확인하고 datetime.date로 변환합니다."""
    return datetime.strptime(str(value), '%Y-%m-%d').date()


def recalculate_summary(date_value):
    """특정 날짜의 결산분석 요약 데이터를 원천 테이블 기준으로 다시 계산해 저장합니다."""
    try:
        d = _safe_date(date_value)
    except Exception:
        return None

    date_str = d.strftime('%Y-%m-%d')
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday = weekdays[d.weekday()]

    conn = get_db_connection()
    c = conn.cursor()

    customer = c.execute("""
        SELECT
            -- 방문/성별/신규 고객 수는 환불 행을 제외하고 계산합니다.
            COALESCE(SUM(CASE WHEN transaction_type!='환불' AND gender='남' THEN 1 ELSE 0 END),0) AS male_count,
            COALESCE(SUM(CASE WHEN transaction_type!='환불' AND gender='여' THEN 1 ELSE 0 END),0) AS female_count,
            COALESCE(SUM(CASE WHEN transaction_type!='환불' AND customer_type='신규' THEN 1 ELSE 0 END),0) AS new_customer_count,
            COALESCE(SUM(CASE WHEN transaction_type!='환불' AND customer_type='구환' THEN 1 ELSE 0 END),0) AS returning_customer_count,
            COALESCE(SUM(CASE WHEN transaction_type!='환불' THEN 1 ELSE 0 END),0) AS total_visit_count,

            -- 매출은 환불 행을 차감 처리합니다.
            -- legacy 고객 CSV는 환불 금액을 양수로 저장하고, 여기서 음수로 반영합니다.
            COALESCE(SUM(CASE WHEN customer_type='신규' THEN
                CASE WHEN transaction_type='환불' THEN -(card_amount + cash_amount + transfer_amount)
                     ELSE card_amount + cash_amount + transfer_amount END
                ELSE 0 END),0) AS new_customer_sales,
            COALESCE(SUM(CASE WHEN customer_type='구환' THEN
                CASE WHEN transaction_type='환불' THEN -(card_amount + cash_amount + transfer_amount)
                     ELSE card_amount + cash_amount + transfer_amount END
                ELSE 0 END),0) AS returning_customer_sales,

            COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -card_amount ELSE card_amount END),0) AS card_treatment_sales,
            COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -cash_amount ELSE cash_amount END),0) AS cash_treatment_sales,
            COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -transfer_amount ELSE transfer_amount END),0) AS transfer_treatment_sales,
            COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -credit_amount ELSE credit_amount END),0) AS credit_used
        FROM customer_records
        WHERE date=?
    """, (date_str,)).fetchone()

    cosmetic = c.execute("""
        SELECT
            COALESCE(SUM(card_amount),0) AS card_cosmetic_sales,
            COALESCE(SUM(cash_amount),0) AS cash_cosmetic_sales,
            COALESCE(SUM(transfer_amount),0) AS transfer_cosmetic_sales,
            COALESCE(SUM(credit_amount),0) AS cosmetic_credit_used
        FROM cosmetic_sales
        WHERE date=?
    """, (date_str,)).fetchone()

    expense = c.execute("""
        SELECT
            COALESCE(SUM(card_amount),0) AS card_expense,
            COALESCE(SUM(cash_amount),0) AS cash_expense
        FROM expenses
        WHERE date=?
    """, (date_str,)).fetchone()

    # customer_excel_entries: 엑셀형 고객입력 데이터를 처음부터 전체 합산합니다.
    excel = c.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN is_refund=0 AND gender='남' THEN 1 ELSE 0 END),0)                     AS male_count,
            COALESCE(SUM(CASE WHEN is_refund=0 AND gender='여' THEN 1 ELSE 0 END),0)                     AS female_count,
            COALESCE(SUM(CASE WHEN is_refund=0 AND customer_type IN ('신환','신규') THEN 1 ELSE 0 END),0) AS new_customer_count,
            COALESCE(SUM(CASE WHEN is_refund=0 AND customer_type='구환' THEN 1 ELSE 0 END),0)            AS returning_customer_count,
            COALESCE(SUM(CASE WHEN is_refund=0 THEN 1 ELSE 0 END),0)                                     AS total_visit_count,
            COALESCE(SUM(CASE WHEN customer_type IN ('신환','신규') THEN net_sales ELSE 0 END),0)        AS new_customer_sales,
            COALESCE(SUM(CASE WHEN customer_type='구환' THEN net_sales ELSE 0 END),0)                   AS returning_customer_sales,
            COALESCE(SUM(card),0)                                                                         AS card_treatment_sales,
            COALESCE(SUM(cash),0)                                                                         AS cash_treatment_sales,
            COALESCE(SUM(transfer),0)                                                                     AS transfer_treatment_sales,
            COALESCE(SUM(net_sales),0)                                                                    AS total_treatment_sales
        FROM customer_excel_entries
        WHERE date=?
    """, (date_str,)).fetchone()

    total_treatment_sales = (
        customer['card_treatment_sales'] + customer['cash_treatment_sales'] + customer['transfer_treatment_sales']
        + excel['total_treatment_sales']
    )
    total_cosmetic_sales = cosmetic['card_cosmetic_sales'] + cosmetic['cash_cosmetic_sales'] + cosmetic['transfer_cosmetic_sales']
    total_daily_sales = total_treatment_sales + total_cosmetic_sales
    total_expense = expense['card_expense'] + expense['cash_expense']
    closing_amount = total_daily_sales - total_expense
    is_workday = 1 if (customer['total_visit_count'] + excel['total_visit_count']) > 0 else 0
    credit_used = customer['credit_used'] + cosmetic['cosmetic_credit_used']

    c.execute("""
        INSERT INTO daily_closing_summary (
            date, year, month, day, weekday,
            male_count, female_count, new_customer_count, returning_customer_count, total_visit_count,
            new_customer_sales, returning_customer_sales,
            card_treatment_sales, cash_treatment_sales, transfer_treatment_sales, total_treatment_sales,
            card_cosmetic_sales, cash_cosmetic_sales, transfer_cosmetic_sales, total_cosmetic_sales,
            total_daily_sales, credit_used,
            card_expense, cash_expense, total_expense,
            closing_amount, is_workday, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(date) DO UPDATE SET
            year=excluded.year,
            month=excluded.month,
            day=excluded.day,
            weekday=excluded.weekday,
            male_count=excluded.male_count,
            female_count=excluded.female_count,
            new_customer_count=excluded.new_customer_count,
            returning_customer_count=excluded.returning_customer_count,
            total_visit_count=excluded.total_visit_count,
            new_customer_sales=excluded.new_customer_sales,
            returning_customer_sales=excluded.returning_customer_sales,
            card_treatment_sales=excluded.card_treatment_sales,
            cash_treatment_sales=excluded.cash_treatment_sales,
            transfer_treatment_sales=excluded.transfer_treatment_sales,
            total_treatment_sales=excluded.total_treatment_sales,
            card_cosmetic_sales=excluded.card_cosmetic_sales,
            cash_cosmetic_sales=excluded.cash_cosmetic_sales,
            transfer_cosmetic_sales=excluded.transfer_cosmetic_sales,
            total_cosmetic_sales=excluded.total_cosmetic_sales,
            total_daily_sales=excluded.total_daily_sales,
            credit_used=excluded.credit_used,
            card_expense=excluded.card_expense,
            cash_expense=excluded.cash_expense,
            total_expense=excluded.total_expense,
            closing_amount=excluded.closing_amount,
            is_workday=excluded.is_workday,
            updated_at=CURRENT_TIMESTAMP
    """, (
        date_str, d.year, d.month, d.day, weekday,
        customer['male_count'] + excel['male_count'],
        customer['female_count'] + excel['female_count'],
        customer['new_customer_count'] + excel['new_customer_count'],
        customer['returning_customer_count'] + excel['returning_customer_count'],
        customer['total_visit_count'] + excel['total_visit_count'],
        customer['new_customer_sales'] + excel['new_customer_sales'],
        customer['returning_customer_sales'] + excel['returning_customer_sales'],
        customer['card_treatment_sales'] + excel['card_treatment_sales'],
        customer['cash_treatment_sales'] + excel['cash_treatment_sales'],
        customer['transfer_treatment_sales'] + excel['transfer_treatment_sales'],
        total_treatment_sales,
        cosmetic['card_cosmetic_sales'], cosmetic['cash_cosmetic_sales'], cosmetic['transfer_cosmetic_sales'], total_cosmetic_sales,
        total_daily_sales, credit_used,
        expense['card_expense'], expense['cash_expense'], total_expense,
        closing_amount, is_workday
    ))

    # ------------------------------------------------------------

    # 고객입력 엑셀형 개편용 테이블

    # - 기존 테이블은 건드리지 않고 없을 때만 생성합니다.

    # - 충전금 사용은 매출에 포함하지 않고 prepaid_usage_entries에 별도 기록합니다.

    # - 수정/삭제 이력은 customer_audit_log에 JSON 문자열로 기록합니다.

    # ------------------------------------------------------------


    c.execute("""

        CREATE TABLE IF NOT EXISTS customer_excel_entries (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            customer_type TEXT,

            gender TEXT,

            customer_name TEXT,

            card INTEGER DEFAULT 0,

            cash INTEGER DEFAULT 0,

            transfer INTEGER DEFAULT 0,

            refund INTEGER DEFAULT 0,

            prepaid INTEGER DEFAULT 0,

            memo TEXT,

            net_sales INTEGER DEFAULT 0,

            is_refund INTEGER DEFAULT 0,

            created_by TEXT NOT NULL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_by TEXT,

            updated_at TEXT

        )

    """)


    c.execute("""

        CREATE TABLE IF NOT EXISTS prepaid_usage_entries (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            customer_name TEXT,

            customer_type TEXT,

            gender TEXT,

            prepaid_usage INTEGER DEFAULT 0,

            memo TEXT,

            source TEXT DEFAULT 'customer_excel',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )

    """)


    c.execute("""

        CREATE TABLE IF NOT EXISTS customer_audit_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            action TEXT NOT NULL,

            target_id INTEGER,

            target_date TEXT,

            before_data TEXT,

            after_data TEXT,

            performed_by TEXT NOT NULL,

            performed_at TEXT DEFAULT CURRENT_TIMESTAMP

        )

    """)


    conn.commit()
    conn.close()
    return date_str


def recalculate_all_summaries():
    """기존 원천 데이터에 존재하는 모든 날짜를 요약 테이블에 반영합니다."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT date FROM customer_records
        UNION SELECT date FROM cosmetic_sales
        UNION SELECT date FROM expenses
        UNION SELECT date FROM daily_closing
        ORDER BY date
    """).fetchall()
    conn.close()
    for row in rows:
        recalculate_summary(row['date'])


if __name__ == '__main__':
    init_db()
