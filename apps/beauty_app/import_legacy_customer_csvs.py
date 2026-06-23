import csv
import os
import re
import sqlite3
from datetime import datetime

from database import get_db_connection, init_db, recalculate_summary

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'legacy_customer_csvs')


def parse_amount(value, refund=False):
    """원화/쉼표/공백이 섞인 금액을 정수로 변환합니다.

    예: '₩1,500,000' -> 1500000, '-₩86,300' -> -86300
    환불 행은 웹앱 계산 방식에 맞춰 양수 금액으로 저장합니다.
    """
    if value is None:
        return 0
    s = str(value).strip()
    if not s or s in ('-', '.', 'nan', 'None'):
        return 0
    s = s.replace('₩', '').replace(',', '').replace(' ', '')
    try:
        amount = int(float(s))
    except ValueError:
        return 0
    return abs(amount) if refund else amount


def normalize_customer_type(value):
    """기존 시트의 신/구 표기를 웹앱의 신규/구환 값으로 변환합니다."""
    s = str(value or '').strip()
    if s in ('신', '신규'):
        return '신규'
    if s in ('구', '구환', '기존'):
        return '구환'
    return None


def normalize_gender(value):
    s = str(value or '').strip()
    if s in ('남', '여'):
        return s
    return None


def normalize_transaction_type(value, has_amount=False):
    """기존 시트의 복합 유형을 현재 웹앱의 단일 유형으로 변환합니다.

    현재 customer_records.transaction_type은 결제/시술/환불/기타 중 하나만 허용합니다.
    그래서 '결제+시술'은 '결제'로 저장하고, 원본 유형은 memo에 남깁니다.
    """
    raw = str(value or '').strip()
    if '환불' in raw:
        return '환불'
    if '결제' in raw:
        return '결제'
    if '시술' in raw:
        return '시술'
    if '기타' in raw:
        return '기타'
    return '결제' if has_amount else '기타'


def find_date_column(fieldnames):
    """날짜 컬럼을 찾습니다. 5고객 CSV처럼 첫 헤더가 깨진 경우도 지원합니다."""
    if '날짜' in fieldnames:
        return '날짜'
    # 첫 컬럼에 날짜값이 들어있는 경우가 있어 첫 컬럼을 날짜 컬럼으로 사용합니다.
    return fieldnames[0]


def parse_date(value):
    """YYYY-MM-DD 또는 YYYY.MM.DD를 YYYY-MM-DD로 통일합니다."""
    s = str(value or '').strip()
    if not s:
        return None
    s = s.replace('.', '-')
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    return None


def import_file(conn, path):
    inserted = 0
    skipped = 0
    affected_dates = set()

    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return inserted, skipped, affected_dates

        date_col = find_date_column(reader.fieldnames)

        for row in reader:
            date = parse_date(row.get(date_col))
            customer_name = str(row.get('고객명', '') or '').strip()
            if not date or not customer_name:
                skipped += 1
                continue

            raw_type = str(row.get('결제,시술,환불,기타', '') or '').strip()
            card_raw = row.get('카드', '')
            cash_raw = row.get('현금', '')
            transfer_raw = row.get('계좌이체', '')
            credit_raw = row.get('충전금 사용', '')
            has_amount = any(str(v or '').strip() for v in [card_raw, cash_raw, transfer_raw, credit_raw])
            transaction_type = normalize_transaction_type(raw_type, has_amount)
            is_refund = transaction_type == '환불'

            card_amount = parse_amount(card_raw, refund=is_refund)
            cash_amount = parse_amount(cash_raw, refund=is_refund)
            transfer_amount = parse_amount(transfer_raw, refund=is_refund)
            credit_amount = parse_amount(credit_raw, refund=is_refund)

            memo_parts = []
            memo = str(row.get('비고', '') or '').strip()
            confirmed_by = str(row.get('확인자', '') or '').strip()
            if raw_type and raw_type != transaction_type:
                memo_parts.append(f'원본유형:{raw_type}')
            if confirmed_by:
                memo_parts.append(f'확인자:{confirmed_by}')
            if memo:
                memo_parts.append(memo)
            final_memo = ' / '.join(memo_parts)

            conn.execute(
                """
                INSERT INTO customer_records (
                    date, transaction_type, customer_type, gender, customer_name, visit_time,
                    card_amount, cash_amount, transfer_amount, credit_amount, memo, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date,
                    transaction_type,
                    normalize_customer_type(row.get('구분')),
                    normalize_gender(row.get('성별')),
                    customer_name,
                    str(row.get('방문시간', '') or '').strip(),
                    card_amount,
                    cash_amount,
                    transfer_amount,
                    credit_amount,
                    final_memo,
                    'legacy_import',
                ),
            )
            inserted += 1
            affected_dates.add(date)

    return inserted, skipped, affected_dates


def main():
    print('DB 테이블 확인/생성 중...')
    init_db()

    if not os.path.isdir(DATA_DIR):
        print(f'CSV 폴더가 없습니다: {DATA_DIR}')
        return

    csv_files = sorted(
        os.path.join(DATA_DIR, name)
        for name in os.listdir(DATA_DIR)
        if name.lower().endswith('.csv')
    )

    if not csv_files:
        print(f'가져올 CSV 파일이 없습니다: {DATA_DIR}')
        return

    conn = get_db_connection()

    # 이 스크립트로 가져온 기존 데이터만 삭제합니다.
    # 웹앱에서 직접 입력한 admin/staff 데이터는 삭제하지 않습니다.
    deleted = conn.execute(
        "DELETE FROM customer_records WHERE created_by = ?",
        ('legacy_import',),
    ).rowcount
    conn.commit()
    print(f'기존 legacy_import 고객 데이터 삭제: {deleted}건')

    total_inserted = 0
    total_skipped = 0
    all_dates = set()

    for path in csv_files:
        inserted, skipped, dates = import_file(conn, path)
        conn.commit()
        total_inserted += inserted
        total_skipped += skipped
        all_dates.update(dates)
        print(f'- {os.path.basename(path)}: 입력 {inserted:,}건, 건너뜀 {skipped:,}건')

    conn.close()

    print('결산분석 요약 재계산 중...')
    for date in sorted(all_dates):
        recalculate_summary(date)

    print('완료')
    print(f'총 입력: {total_inserted:,}건')
    print(f'총 건너뜀: {total_skipped:,}건')
    print(f'요약 재계산 날짜 수: {len(all_dates):,}일')
    print('이제 py app.py로 서버를 실행한 뒤 고객입력/결산분석 화면에서 확인하세요.')


if __name__ == '__main__':
    main()
