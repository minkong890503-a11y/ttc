from datetime import datetime, timedelta
import json
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from database import get_db_connection, init_db, recalculate_summary, recalculate_all_summaries

app = Flask(__name__)
app.secret_key = os.environ.get('BEAUTY_APP_SECRET_KEY', 'change-me-in-production')

def to_int(v):
    try: return max(0, int(str(v or 0).replace(',', '')))
    except ValueError: return 0

def login_required(f):
    @wraps(f)
    def w(*args, **kwargs):
        if 'user_name' not in session:
            flash('로그인이 필요합니다.'); return redirect(url_for('login'))
        return f(*args, **kwargs)
    return w


def role_required(*roles):
    """특정 권한만 접근할 수 있도록 제한합니다."""
    def deco(f):
        @wraps(f)
        def w(*args, **kwargs):
            if 'user_name' not in session:
                flash('로그인이 필요합니다.')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('접근 권한이 없습니다.')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return w
    return deco

def money(v): return f"{int(v or 0):,}"
app.jinja_env.filters['money'] = money

@app.route('/health')
def health(): return {'status':'ok','message':'beauty_app_step10_beta is running'}

@app.route('/')
def index(): return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name','').strip(); pw = request.form.get('password','')
        conn = get_db_connection(); user = conn.execute('SELECT * FROM users WHERE name=? AND is_active=1', (name,)).fetchone(); conn.close()
        if user and check_password_hash(user['password'], pw):
            session.clear(); session['user_id']=user['id']; session['user_name']=user['name']; session['role']=user['role']
            flash('로그인되었습니다.'); return redirect(url_for('dashboard'))
        flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); flash('로그아웃되었습니다.'); return redirect(url_for('login'))

def aggregate(date):
    conn = get_db_connection()
    cust = conn.execute('SELECT * FROM customer_records WHERE date=?', (date,)).fetchall()
    treatment_card=treatment_cash=treatment_transfer=credit_used=0; total_visit=male=female=newcnt=0; new_sales=old_sales=0; cash_refund=0
    for r in cust:
        sign = -1 if r['transaction_type']=='환불' else 1
        card=(r['card_amount'] or 0)*sign; cash=(r['cash_amount'] or 0)*sign; trans=(r['transfer_amount'] or 0)*sign; credit=(r['credit_amount'] or 0)*sign
        treatment_card += card; treatment_cash += cash; treatment_transfer += trans; credit_used += credit
        if r['transaction_type']=='환불': cash_refund += (r['cash_amount'] or 0)
        if r['transaction_type'] in ('결제','시술','기타'):
            total_visit += 1
            if r['gender']=='남': male += 1
            if r['gender']=='여': female += 1
            if r['customer_type']=='신규': newcnt += 1
        if r['customer_type']=='신규': new_sales += card+cash+trans
        else: old_sales += card+cash+trans
    cos = conn.execute('SELECT COALESCE(SUM(card_amount),0) card, COALESCE(SUM(cash_amount),0) cash, COALESCE(SUM(transfer_amount),0) trans, COALESCE(SUM(credit_amount),0) credit FROM cosmetic_sales WHERE date=?', (date,)).fetchone()
    exp = conn.execute('SELECT COALESCE(SUM(card_amount),0) card, COALESCE(SUM(cash_amount),0) cash FROM expenses WHERE date=?', (date,)).fetchone()
    prev = conn.execute('SELECT actual_cash FROM cash_closing WHERE date < ? AND actual_cash IS NOT NULL ORDER BY date DESC LIMIT 1', (date,)).fetchone()
    actual = conn.execute('SELECT actual_cash FROM cash_closing WHERE date=?', (date,)).fetchone()
    conn.close()
    prev_cash = prev['actual_cash'] if prev else 0
    actual_cash = actual['actual_cash'] if actual and actual['actual_cash'] is not None else None
    cosmetic_card, cosmetic_cash, cosmetic_transfer, cosmetic_credit = cos['card'], cos['cash'], cos['trans'], cos['credit']
    expense_card, expense_cash = exp['card'], exp['cash']
    total_treatment_sales = treatment_card + treatment_cash + treatment_transfer
    total_cosmetic_sales = cosmetic_card + cosmetic_cash + cosmetic_transfer
    total_sales = total_treatment_sales + total_cosmetic_sales
    total_expense = expense_card + expense_cash
    cash_sales = treatment_cash + cosmetic_cash
    expected_cash = prev_cash + cash_sales - cash_refund - expense_cash
    diff = None if actual_cash is None else actual_cash - expected_cash
    if not cust and total_cosmetic_sales==0 and total_expense==0: status='미결산'
    elif actual_cash is None: status='시재미입력'
    elif diff == 0: status='확인완료'
    else: status='차액발생'
    return dict(date=date, male_count=male, female_count=female, new_count=newcnt, total_visit=total_visit, new_sales=new_sales, old_sales=old_sales, treatment_card=treatment_card, treatment_cash=treatment_cash, treatment_transfer=treatment_transfer, total_treatment_sales=total_treatment_sales, cosmetic_card=cosmetic_card, cosmetic_cash=cosmetic_cash, cosmetic_transfer=cosmetic_transfer, total_cosmetic_sales=total_cosmetic_sales, credit_used=credit_used+cosmetic_credit, total_card_sales=treatment_card+cosmetic_card, total_cash_sales=treatment_cash+cosmetic_cash, total_transfer_sales=treatment_transfer+cosmetic_transfer, total_sales=total_sales, expense_card=expense_card, expense_cash=expense_cash, total_expense=total_expense, net_profit=total_sales-total_expense, prev_cash=prev_cash, cash_sales=cash_sales, cash_refund=cash_refund, expected_cash=expected_cash, actual_cash=actual_cash, cash_difference=diff, status=status)

@app.route('/dashboard')
@login_required
def dashboard():
    today=datetime.now().strftime('%Y-%m-%d'); agg=aggregate(today)
    conn=get_db_connection()
    rows=[]
    for q in ["SELECT '고객' type,date,customer_name title,transaction_type detail,created_at FROM customer_records ORDER BY created_at DESC LIMIT 5", "SELECT '화장품' type,date,customer_name title,product_name detail,created_at FROM cosmetic_sales ORDER BY created_at DESC LIMIT 5", "SELECT '지출' type,date,category title,description detail,created_at FROM expenses ORDER BY created_at DESC LIMIT 5"]:
        rows += [dict(x) for x in conn.execute(q).fetchall()]
    conn.close(); rows.sort(key=lambda x:x.get('created_at') or '', reverse=True)
    return render_template('dashboard.html', agg=agg, recent=rows[:5], today=today)

@app.route('/customers/new', methods=['GET','POST'])
@login_required
def customer_input():
    conn=get_db_connection()
    if request.method=='POST':
        date=request.form.get('date') or datetime.now().strftime('%Y-%m-%d'); visit=request.form.get('visit_time') or datetime.now().strftime('%H:%M')
        name=request.form.get('customer_name','').strip(); t=request.form.get('transaction_type'); ctype=request.form.get('customer_type') or None; gender=request.form.get('gender') or None
        if not name: flash('고객명을 입력해주세요.'); return redirect(url_for('customer_input'))
        vals=(date,t,ctype,gender,name,visit,to_int(request.form.get('card_amount')),to_int(request.form.get('cash_amount')),to_int(request.form.get('transfer_amount')),to_int(request.form.get('credit_amount')),request.form.get('memo','').strip(),session['user_name'])
        conn.execute('INSERT INTO customer_records(date,transaction_type,customer_type,gender,customer_name,visit_time,card_amount,cash_amount,transfer_amount,credit_amount,memo,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', vals)
        conn.commit(); recalculate_summary(date); flash('고객 기록이 저장되었습니다.'); return redirect(url_for('customer_input'))
    records=conn.execute('SELECT * FROM customer_records ORDER BY date DESC,id DESC LIMIT 10').fetchall(); conn.close()
    return render_template('customer_input.html', today=datetime.now().strftime('%Y-%m-%d'), now_time=datetime.now().strftime('%H:%M'), records=records)

@app.route('/cosmetics/inventory', methods=['GET','POST'])
@login_required
def inventory():
    conn=get_db_connection()
    if request.method=='POST':
        name=request.form.get('product_name','').strip(); qty=to_int(request.form.get('stock_quantity')); unit=to_int(request.form.get('unit_price')); total=to_int(request.form.get('total_amount'))
        if not name: flash('제품명을 입력해주세요.'); return redirect(url_for('inventory'))
        if qty>0 and unit>0 and total==0: total=qty*unit
        elif qty>0 and total>0 and unit==0: unit=total//qty
        existing=conn.execute('SELECT * FROM cosmetic_inventory WHERE product_name=?',(name,)).fetchone()
        if existing:
            new_qty=existing['stock_quantity']+qty; conn.execute('UPDATE cosmetic_inventory SET stock_quantity=?,unit_price=?,total_amount=?,memo=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(new_qty,unit,new_qty*unit,request.form.get('memo',''),existing['id']))
        else:
            conn.execute('INSERT INTO cosmetic_inventory(product_name,stock_quantity,unit_price,total_amount,memo,created_by) VALUES (?,?,?,?,?,?)',(name,qty,unit,total,request.form.get('memo',''),session['user_name']))
        conn.commit(); flash('재고가 저장되었습니다.'); return redirect(url_for('inventory'))
    products=conn.execute('SELECT * FROM cosmetic_inventory ORDER BY product_name').fetchall(); conn.close(); return render_template('cosmetic_inventory.html', products=products)

@app.route('/cosmetics/new', methods=['GET','POST'])
@login_required
def cosmetic_input():
    conn=get_db_connection()
    if request.method=='POST':
        try: items=json.loads(request.form.get('items_json','[]'))
        except Exception: items=[]
        valid=[]
        for item in items:
            pid=to_int(item.get('product_id')); qty=to_int(item.get('quantity'))
            p=conn.execute('SELECT * FROM cosmetic_inventory WHERE id=?',(pid,)).fetchone() if pid else None
            if p and qty>0:
                if p['stock_quantity'] < qty: flash(f"{p['product_name']} 재고가 부족합니다."); return redirect(url_for('cosmetic_input'))
                valid.append((p,qty))
        if not valid: flash('판매 제품을 선택해주세요.'); return redirect(url_for('cosmetic_input'))
        names=', '.join([p['product_name'] for p,q in valid]); total_qty=sum(q for p,q in valid)
        cur=conn.execute('INSERT INTO cosmetic_sales(date,staff_name,customer_name,product_name,quantity,card_amount,cash_amount,transfer_amount,credit_amount,memo,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(request.form.get('date'), request.form.get('staff_name') or session['user_name'], request.form.get('customer_name',''), names, total_qty, to_int(request.form.get('card_amount')), to_int(request.form.get('cash_amount')), to_int(request.form.get('transfer_amount')), to_int(request.form.get('credit_amount')), request.form.get('memo',''), session['user_name']))
        sid=cur.lastrowid
        for p,q in valid:
            line=p['unit_price']*q; conn.execute('INSERT INTO cosmetic_sale_items(sale_id,product_id,product_name,quantity,unit_price,line_total) VALUES (?,?,?,?,?,?)',(sid,p['id'],p['product_name'],q,p['unit_price'],line)); newq=p['stock_quantity']-q; conn.execute('UPDATE cosmetic_inventory SET stock_quantity=?,total_amount=? WHERE id=?',(newq,newq*p['unit_price'],p['id']))
        conn.commit(); recalculate_summary(request.form.get('date')); flash('화장품 판매가 저장되었습니다.'); return redirect(url_for('cosmetic_input'))
    products=conn.execute('SELECT * FROM cosmetic_inventory ORDER BY product_name').fetchall(); sales=conn.execute('SELECT * FROM cosmetic_sales ORDER BY date DESC,id DESC LIMIT 10').fetchall(); conn.close(); return render_template('cosmetic_input.html', today=datetime.now().strftime('%Y-%m-%d'), products=products, products_json=json.dumps([dict(p) for p in products], ensure_ascii=False), sales=sales)

@app.route('/expenses/new', methods=['GET','POST'])
@login_required
def expense_input():
    conn=get_db_connection()
    if request.method=='POST':
        date=request.form.get('date')
        conn.execute('INSERT INTO expenses(date,category,description,card_amount,cash_amount,memo,created_by) VALUES (?,?,?,?,?,?,?)',(date,request.form.get('category'),request.form.get('description'),to_int(request.form.get('card_amount')),to_int(request.form.get('cash_amount')),request.form.get('memo',''),session['user_name'])); conn.commit(); recalculate_summary(date); flash('지출이 저장되었습니다.'); return redirect(url_for('expense_input'))
    expenses=conn.execute('SELECT * FROM expenses ORDER BY date DESC,id DESC LIMIT 10').fetchall(); conn.close(); return render_template('expense_input.html', today=datetime.now().strftime('%Y-%m-%d'), expenses=expenses)

@app.route('/closing/cash', methods=['GET','POST'])
@login_required
def cash_closing():
    today=datetime.now().strftime('%Y-%m-%d'); date=request.values.get('date') or today
    conn=get_db_connection()
    if request.method=='POST':
        actual=to_int(request.form.get('actual_cash')); agg=aggregate(date); diff=actual-agg['expected_cash']; existing=conn.execute('SELECT id FROM cash_closing WHERE date=?',(date,)).fetchone()
        if existing: conn.execute('UPDATE cash_closing SET prev_cash=?,cash_sales=?,cash_expense=?,expected_cash=?,actual_cash=?,difference=?,confirmed_by=?,updated_at=CURRENT_TIMESTAMP WHERE date=?',(agg['prev_cash'],agg['cash_sales'],agg['expense_cash'],agg['expected_cash'],actual,diff,session['user_name'],date))
        else: conn.execute('INSERT INTO cash_closing(date,prev_cash,cash_sales,cash_expense,expected_cash,actual_cash,difference,confirmed_by) VALUES (?,?,?,?,?,?,?,?)',(date,agg['prev_cash'],agg['cash_sales'],agg['expense_cash'],agg['expected_cash'],actual,diff,session['user_name']))
        conn.commit(); recalculate_summary(date); flash('시재가 저장되었습니다.'); return redirect(url_for('cash_closing', date=date))
    closings=conn.execute('SELECT * FROM cash_closing ORDER BY date DESC LIMIT 10').fetchall(); conn.close(); return render_template('cash_closing.html', today=today, selected_date=date, agg=aggregate(date), closings=closings)

@app.route('/closing/daily', methods=['GET','POST'])
@login_required
def daily_closing():
    today=datetime.now().strftime('%Y-%m-%d'); date=request.values.get('date') or today; agg=aggregate(date); conn=get_db_connection()
    if request.method=='POST':
        version=(conn.execute('SELECT COALESCE(MAX(version),0) v FROM daily_closing WHERE date=?',(date,)).fetchone()['v'] or 0)+1
        conn.execute('INSERT INTO daily_closing(date,version,total_card_sales,total_cash_sales,total_transfer_sales,total_credit_used,total_treatment_sales,total_cosmetic_sales,total_sales,total_card_expense,total_cash_expense,total_expense,net_profit,expected_cash,actual_cash,cash_difference,status,saved_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(date,version,agg['total_card_sales'],agg['total_cash_sales'],agg['total_transfer_sales'],agg['credit_used'],agg['total_treatment_sales'],agg['total_cosmetic_sales'],agg['total_sales'],agg['expense_card'],agg['expense_cash'],agg['total_expense'],agg['net_profit'],agg['expected_cash'],agg['actual_cash'] or 0,agg['cash_difference'] or 0,agg['status'],session['user_name']))
        conn.commit(); recalculate_summary(date); flash(f'결산이 v{version}으로 저장되었습니다.'); return redirect(url_for('daily_closing', date=date))
    history=conn.execute('SELECT * FROM daily_closing WHERE date=? ORDER BY version DESC',(date,)).fetchall(); conn.close(); return render_template('daily_closing.html', today=today, selected_date=date, agg=agg, history=history)

@app.route('/closing/monthly')
@login_required
def monthly_closing():
    year=request.args.get('year') or datetime.now().strftime('%Y'); rows=[]; totals={'total_visit':0,'new_count':0,'total_treatment_sales':0,'total_cosmetic_sales':0,'total_sales':0,'total_expense':0,'net_profit':0}
    for m in range(1,13):
        prefix=f'{year}-{m:02d}'; conn=get_db_connection();
        c=conn.execute("SELECT COUNT(*) cnt, COALESCE(SUM(CASE WHEN customer_type='신규' THEN 1 ELSE 0 END),0) newcnt, COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -(card_amount+cash_amount+transfer_amount) ELSE card_amount+cash_amount+transfer_amount END),0) sales FROM customer_records WHERE date LIKE ?", (prefix+'%',)).fetchone()
        cs=conn.execute('SELECT COALESCE(SUM(card_amount+cash_amount+transfer_amount),0) sales FROM cosmetic_sales WHERE date LIKE ?', (prefix+'%',)).fetchone(); e=conn.execute('SELECT COALESCE(SUM(card_amount+cash_amount),0) amount FROM expenses WHERE date LIKE ?', (prefix+'%',)).fetchone(); conn.close()
        row={'month':m,'total_visit':c['cnt'],'new_count':c['newcnt'],'total_treatment_sales':c['sales'],'total_cosmetic_sales':cs['sales'],'total_sales':c['sales']+cs['sales'],'total_expense':e['amount'],'net_profit':c['sales']+cs['sales']-e['amount']}; rows.append(row)
        for k in totals: totals[k]+=row[k]
    return render_template('monthly_closing.html', year=year, rows=rows, totals=totals)

@app.route('/staff/sales')
@login_required
def staff_sales():
    start=request.args.get('start_date') or datetime.now().strftime('%Y-%m-01'); end=request.args.get('end_date') or datetime.now().strftime('%Y-%m-%d'); conn=get_db_connection(); mp={}
    for r in conn.execute("SELECT created_by staff, COALESCE(SUM(CASE WHEN transaction_type='환불' THEN -(card_amount+cash_amount+transfer_amount) ELSE card_amount+cash_amount+transfer_amount END),0) sales FROM customer_records WHERE date BETWEEN ? AND ? GROUP BY created_by", (start,end)).fetchall(): mp.setdefault(r['staff'], {'staff_name':r['staff'],'treatment_sales':0,'cosmetic_sales':0})['treatment_sales']=r['sales']
    for r in conn.execute('SELECT staff_name staff, COALESCE(SUM(card_amount+cash_amount+transfer_amount),0) sales FROM cosmetic_sales WHERE date BETWEEN ? AND ? GROUP BY staff_name', (start,end)).fetchall(): mp.setdefault(r['staff'], {'staff_name':r['staff'],'treatment_sales':0,'cosmetic_sales':0})['cosmetic_sales']=r['sales']
    conn.close(); rows=list(mp.values())
    for r in rows: r['total_sales']=r['treatment_sales']+r['cosmetic_sales']
    rows.sort(key=lambda x:x['total_sales'], reverse=True); return render_template('staff_sales.html', start_date=start, end_date=end, rows=rows)



def _parse_month(value):
    try:
        return datetime.strptime(value, '%Y-%m')
    except Exception:
        return datetime.now().replace(day=1)


def _month_bounds(month_text):
    m = _parse_month(month_text)
    start = m.strftime('%Y-%m-01')
    if m.month == 12:
        nxt = m.replace(year=m.year + 1, month=1, day=1)
    else:
        nxt = m.replace(month=m.month + 1, day=1)
    end = (nxt - timedelta(days=1)).strftime('%Y-%m-%d')
    return m, start, end


def _previous_month_text(month_text):
    m = _parse_month(month_text)
    if m.month == 1:
        p = m.replace(year=m.year - 1, month=12, day=1)
    else:
        p = m.replace(month=m.month - 1, day=1)
    return p.strftime('%Y-%m')


def _get_summary_row(date_text):
    recalculate_summary(date_text)
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM daily_closing_summary WHERE date=?', (date_text,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _card_data(row):
    if not row:
        return {'date': None, 'message': '데이터 없음', 'total_visit_count': 0, 'new_customer_sales': 0, 'returning_customer_sales': 0, 'total_daily_sales': 0, 'total_expense': 0, 'closing_amount': 0}
    return {'date': row['date'], 'total_visit_count': row['total_visit_count'], 'new_customer_sales': row['new_customer_sales'], 'returning_customer_sales': row['returning_customer_sales'], 'total_daily_sales': row['total_daily_sales'], 'total_expense': row['total_expense'], 'closing_amount': row['closing_amount']}


def _month_rows(month_text, workday_only=False):
    # recalculate_all_summaries()  # 그래프 조회 중 DB lock 방지를 위해 비활성화
    m, start, end = _month_bounds(month_text)
    conn = get_db_connection()
    sql = 'SELECT * FROM daily_closing_summary WHERE date BETWEEN ? AND ?'
    params = [start, end]
    if workday_only:
        sql += ' AND is_workday=1'
    sql += ' ORDER BY date'
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def _average_months(month_text, average):
    cur = _parse_month(month_text)
    conn = get_db_connection()
    months = [r['ym'] for r in conn.execute("SELECT DISTINCT substr(date,1,7) ym FROM daily_closing_summary WHERE substr(date,1,7) < ? ORDER BY ym", (cur.strftime('%Y-%m'),)).fetchall()]
    conn.close()
    if average == '3m':
        months = months[-3:]
    elif average == '6m':
        months = months[-6:]
    return months


def _sum_rows(rows):
    keys = ['new_customer_sales','returning_customer_sales','total_daily_sales','total_visit_count','closing_amount']
    return {k: sum(int(r.get(k) or 0) for r in rows) for k in keys}


def _same_day_value(month_text, day, key):
    target = f'{month_text}-{int(day):02d}'
    row = _get_summary_row(target)
    return int(row.get(key) or 0) if row else 0


@app.route('/analytics')
@role_required('manager', 'owner')
def analytics():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('analytics.html', today=today, current_month=today[:7])


@app.route('/api/analytics/summary')
@role_required('manager', 'owner')
def analytics_summary():
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    selected_date = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    average = request.args.get('average') or 'all'
    if not selected_date.startswith(month):
        return jsonify({'error': '선택 날짜가 기준 월 밖입니다.'}), 400
    today = datetime.now().strftime('%Y-%m-%d')
    today_row = _get_summary_row(today)
    selected_row = _get_summary_row(selected_date)
    rows = _month_rows(month)
    cumulative = _sum_rows(rows)
    prev_month = _previous_month_text(month)
    day = int(selected_date[-2:])
    selected_sales = int(selected_row.get('total_daily_sales') or 0) if selected_row else 0
    selected_visit = int(selected_row.get('total_visit_count') or 0) if selected_row else 0
    prev_sales = _same_day_value(prev_month, day, 'total_daily_sales')
    prev_visit = _same_day_value(prev_month, day, 'total_visit_count')
    months = _average_months(month, average)
    avg_sales = avg_visit = 0
    if months:
        avg_sales = round(sum(_same_day_value(m, day, 'total_daily_sales') for m in months) / len(months))
        avg_visit = round(sum(_same_day_value(m, day, 'total_visit_count') for m in months) / len(months))
    return jsonify({
        'today': _card_data(today_row),
        'selected': _card_data(selected_row),
        'month_cumulative': cumulative,
        'comparison': {
            'vs_lastmonth_sales': selected_sales - prev_sales,
            'vs_average_sales': selected_sales - avg_sales,
            'vs_lastmonth_visit': selected_visit - prev_visit,
            'vs_average_visit': selected_visit - avg_visit,
        },
        'has_data': any((r.get('total_visit_count') or 0) or (r.get('total_daily_sales') or 0) or (r.get('total_expense') or 0) for r in rows)
    })


def _series_calendar(rows, key, days):
    by_day = {int(r['day']): int(r.get(key) or 0) for r in rows}
    out=[]; running=0
    for d in range(1, days+1):
        running += by_day.get(d, 0)
        out.append(running if d in by_day or running else None)
    return out


def _series_workday(rows, key):
    out=[]; running=0
    for r in rows:
        running += int(r.get(key) or 0)
        out.append(running)
    return out


def _average_series(month_text, key, basis, average, length):
    months = _average_months(month_text, average)
    if not months:
        return [None] * length
    collected=[]
    for m in months:
        rows = _month_rows(m, workday_only=(basis=='workday'))
        if basis == 'workday':
            arr = _series_workday(rows, key)
        else:
            dt, start, end = _month_bounds(m)
            days = int(end[-2:])
            arr = _series_calendar(rows, key, days)
        if arr:
            collected.append(arr)
    if not collected:
        return [None] * length
    result=[]
    for i in range(length):
        vals=[a[i] for a in collected if i < len(a) and a[i] is not None]
        result.append(round(sum(vals)/len(vals)) if vals else None)
    return result


@app.route('/api/analytics/trend')
@role_required('manager', 'owner')
def analytics_trend():
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    basis = request.args.get('basis') or 'calendar'
    average = request.args.get('average') or 'all'
    current_rows = _month_rows(month, workday_only=(basis=='workday'))
    previous_month = _previous_month_text(month)
    previous_rows = _month_rows(previous_month, workday_only=(basis=='workday'))
    if basis == 'workday':
        length = max(len(current_rows), len(previous_rows), 1)
        labels = [str(i) for i in range(1, length+1)]
    else:
        dt, start, end = _month_bounds(month)
        length = int(end[-2:])
        labels = [str(i) for i in range(1, length+1)]
    keys = {
        'new_customer_sales': '신환매출',
        'returning_customer_sales': '구환매출',
        'total_daily_sales': '일일총매출',
        'new_customer_count': '신규 고객 수',
        'returning_customer_count': '구환 고객 수',
        'total_visit_count': '총내원 수',
    }
    charts={}
    for key, title in keys.items():
        if basis == 'workday':
            cur = _series_workday(current_rows, key)
            prev = _series_workday(previous_rows, key)
        else:
            cur = _series_calendar(current_rows, key, length)
            prev_dt, ps, pe = _month_bounds(previous_month)
            prev = _series_calendar(previous_rows, key, int(pe[-2:]))
        cur = (cur + [None]*length)[:length]
        prev = (prev + [None]*length)[:length]
        avg = _average_series(month, key, basis, average, length)
        charts[key] = {'title': title, 'current': cur, 'previous': prev, 'average': avg}
    return jsonify({'labels': labels, 'charts': charts, 'has_data': any((r.get('total_visit_count') or 0) or (r.get('total_daily_sales') or 0) or (r.get('total_expense') or 0) for r in current_rows)})


@app.route('/api/analytics/weekday')
@role_required('manager', 'owner')
def analytics_weekday():
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    average = request.args.get('average') or 'all'
    labels = ['월','화','수','목','금','토','일']
    keys = {
        'new_customer_sales': '신환매출',
        'returning_customer_sales': '구환매출',
        'total_daily_sales': '일일총매출',
        'new_customer_count': '신규 고객 수',
        'returning_customer_count': '구환 고객 수',
        'total_visit_count': '총내원 수',
        'avg_daily_visit': '일평균 방문자 수',
    }
    def values_for(month_text, key):
        rows = _month_rows(month_text)
        out=[]
        for w in labels:
            wr=[r for r in rows if r['weekday']==w]
            if key == 'avg_daily_visit':
                vals=[int(r.get('total_visit_count') or 0) for r in wr if int(r.get('is_workday') or 0)==1]
                out.append(round(sum(vals)/len(vals), 1) if vals else None)
            else:
                out.append(round(sum(int(r.get(key) or 0) for r in wr)/len(wr), 1) if wr else None)
        return out
    prev = _previous_month_text(month)
    avg_months = _average_months(month, average)
    charts={}
    for key,title in keys.items():
        current = values_for(month, key)
        previous = values_for(prev, key)
        if avg_months:
            month_values=[values_for(m, key) for m in avg_months]
            avg=[]
            for i in range(7):
                vals=[mv[i] for mv in month_values if mv[i] is not None]
                avg.append(round(sum(vals)/len(vals), 1) if vals else None)
        else:
            avg=[None]*7
        charts[key]={'title': title, 'current': current, 'previous': previous, 'average': avg}
    return jsonify({'labels': labels, 'charts': charts})

@app.route('/settings')
@login_required
def settings(): return render_template('settings.html')

@app.route("/api/analytics/summary_v2")
def analytics_summary_v2():
    import sqlite3
    from datetime import date, datetime, timedelta

    db_path = "beauty_app.db"
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"]

    def safe_int(value):
        return int(value or 0)

    def row_to_dict(row):
        return dict(row) if row else None

    def parse_month(value):
        try:
            y, m = value.split("-")
            return int(y), int(m)
        except Exception:
            today = date.today()
            return today.year, today.month

    def parse_selected_date(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return date.today()

    def previous_month(year, month):
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def direction(value):
        if value > 0:
            return "up"
        if value < 0:
            return "down"
        return "neutral"

    def empty_day(target_date):
        return {
            "date": target_date.isoformat(),
            "weekday": weekday_ko[target_date.weekday()],
            "total_visit_count": 0,
            "new_customer_sales": 0,
            "returning_customer_sales": 0,
            "total_daily_sales": 0,
            "total_expense": 0,
            "closing_amount": 0,
        }

    month_param = request.args.get("month", "")
    date_param = request.args.get("date", "")
    average = request.args.get("average", "all")

    year, month = parse_month(month_param)
    selected_date = parse_selected_date(date_param)

    if selected_date.year != year or selected_date.month != month:
        return jsonify({"ok": False, "error": "선택 날짜가 기준 월 밖입니다."}), 400

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    today_date = date.today()
    today_row = conn.execute("SELECT * FROM daily_closing_summary WHERE date = ?", (today_date.isoformat(),)).fetchone()
    selected_row = conn.execute("SELECT * FROM daily_closing_summary WHERE date = ?", (selected_date.isoformat(),)).fetchone()

    today_data = row_to_dict(today_row) or empty_day(today_date)
    selected_data = row_to_dict(selected_row) or empty_day(selected_date)

    cumulative_sql = """
        SELECT
            SUM(total_visit_count) AS total_visit_count,
            SUM(new_customer_sales) AS new_customer_sales,
            SUM(returning_customer_sales) AS returning_customer_sales,
            SUM(total_daily_sales) AS total_daily_sales,
            SUM(total_expense) AS total_expense,
            SUM(closing_amount) AS closing_amount
        FROM daily_closing_summary
        WHERE year = ? AND month = ? AND date <= ?
    """
    cumulative_row = conn.execute(cumulative_sql, (year, month, selected_date.isoformat())).fetchone()
    cumulative = row_to_dict(cumulative_row) or {}

    prev_year, prev_month = previous_month(selected_date.year, selected_date.month)
    selected_weekday = weekday_ko[selected_date.weekday()]

    lastmonth_sql = """
        SELECT
            AVG(total_daily_sales) AS avg_sales,
            AVG(total_visit_count) AS avg_visit
        FROM daily_closing_summary
        WHERE year = ?
          AND month = ?
          AND weekday = ?
          AND is_workday = 1
    """
    lastmonth_row = conn.execute(lastmonth_sql, (prev_year, prev_month, selected_weekday)).fetchone()
    lastmonth_data = row_to_dict(lastmonth_row) or {}

    avg_where = "WHERE is_workday = 1"
    avg_params = []

    if average == "3m":
        start = selected_date - timedelta(days=92)
        avg_where += " AND date >= ? AND date <= ?"
        avg_params.extend([start.isoformat(), selected_date.isoformat()])
    elif average == "6m":
        start = selected_date - timedelta(days=183)
        avg_where += " AND date >= ? AND date <= ?"
        avg_params.extend([start.isoformat(), selected_date.isoformat()])

    avg_sql = f"""
        SELECT
            AVG(total_daily_sales) AS average_sales,
            AVG(total_visit_count) AS average_visit
        FROM daily_closing_summary
        {avg_where}
    """
    avg_row = conn.execute(avg_sql, avg_params).fetchone()
    avg_data = row_to_dict(avg_row) or {}
    conn.close()

    selected_sales = safe_int(selected_data.get("total_daily_sales"))
    selected_visit = safe_int(selected_data.get("total_visit_count"))
    lastmonth_avg_sales = int(round(lastmonth_data.get("avg_sales") or 0))
    lastmonth_avg_visit = int(round(lastmonth_data.get("avg_visit") or 0))
    average_sales = int(round(avg_data.get("average_sales") or 0))
    average_visit = int(round(avg_data.get("average_visit") or 0))

    vs_lastmonth_weekday_sales = selected_sales - lastmonth_avg_sales
    vs_lastmonth_weekday_visit = selected_visit - lastmonth_avg_visit
    vs_average_sales = selected_sales - average_sales
    vs_average_visit = selected_visit - average_visit

    return jsonify({
        "ok": True,
        "today": {
            "date": today_data.get("date"),
            "weekday": today_data.get("weekday"),
            "total_visit_count": safe_int(today_data.get("total_visit_count")),
            "new_customer_sales": safe_int(today_data.get("new_customer_sales")),
            "returning_customer_sales": safe_int(today_data.get("returning_customer_sales")),
            "total_daily_sales": safe_int(today_data.get("total_daily_sales")),
            "total_expense": safe_int(today_data.get("total_expense")),
            "closing_amount": safe_int(today_data.get("closing_amount")),
        },
        "selected": {
            "date": selected_data.get("date"),
            "weekday": selected_data.get("weekday"),
            "total_visit_count": selected_visit,
            "new_customer_sales": safe_int(selected_data.get("new_customer_sales")),
            "returning_customer_sales": safe_int(selected_data.get("returning_customer_sales")),
            "total_daily_sales": selected_sales,
            "total_expense": safe_int(selected_data.get("total_expense")),
            "closing_amount": safe_int(selected_data.get("closing_amount")),
        },
        "month_cumulative": {
            "total_visit_count": safe_int(cumulative.get("total_visit_count")),
            "new_customer_sales": safe_int(cumulative.get("new_customer_sales")),
            "returning_customer_sales": safe_int(cumulative.get("returning_customer_sales")),
            "total_daily_sales": safe_int(cumulative.get("total_daily_sales")),
            "total_expense": safe_int(cumulative.get("total_expense")),
            "closing_amount": safe_int(cumulative.get("closing_amount")),
        },
        "comparison": {
            "today_weekday": selected_weekday,
            "vs_lastmonth_weekday_sales": vs_lastmonth_weekday_sales,
            "vs_lastmonth_weekday_sales_direction": direction(vs_lastmonth_weekday_sales),
            "vs_average_sales": vs_average_sales,
            "vs_average_sales_direction": direction(vs_average_sales),
            "vs_lastmonth_weekday_visit": vs_lastmonth_weekday_visit,
            "vs_lastmonth_weekday_visit_direction": direction(vs_lastmonth_weekday_visit),
            "vs_average_visit": vs_average_visit,
            "vs_average_visit_direction": direction(vs_average_visit),
            "lastmonth_weekday_avg_sales": lastmonth_avg_sales,
            "lastmonth_weekday_avg_visit": lastmonth_avg_visit,
            "average_sales": average_sales,
            "average_visit": average_visit,
        }
    })

# 기존 /api/analytics/weekday 라우트 아래,


# -------------------------------------------------------------------
# 고객 엑셀형 빠른 입력
# - 거래유형/방문시간 없이 입력
# - 고객명 입력 시 날짜가 비어 있으면 오늘 날짜 자동 입력
# - 환불은 양수 입력, 저장 시 매출에 마이너스 반영
# - 환불 값이 있으면 방문수/신환/구환/성별 카운트 제외
# -------------------------------------------------------------------
@app.route("/customers/excel-input")
def customer_excel_input_page():
    from flask import render_template_string

    html = """
    {% extends 'base.html' %}
    {% block content %}
    <div class="page-header">
      <h2>고객 엑셀형 입력</h2>
      <p class="text-muted">여러 고객 결제 내역을 표 형태로 빠르게 입력합니다.</p>
    </div>

    <div class="excel-input-guide">
      <strong>입력 규칙</strong>
      <ul>
        <li>고객명을 입력하면 날짜가 비어 있을 때 오늘 날짜가 자동 입력됩니다.</li>
        <li>환불은 양수로 입력하면 저장 시 매출에서 자동 차감됩니다.</li>
        <li>충전금 사용은 매출에 포함하지 않고 별도로 관리됩니다.</li>
        <li>충전금 사용은 매출에 포함하지 않고 별도로 관리됩니다.</li>
        <li>환불 금액이 있는 행은 방문수/신환/구환/성별 카운트에서 제외됩니다.</li>
        <li>환불 행에는 카드/현금/계좌이체/충전금 사용 금액을 같이 입력하지 않는 것을 권장합니다.</li>
      </ul>
    </div>

    <div class="excel-toolbar">
      <button type="button" id="excel-add-row-btn">행 추가</button>
      <button type="button" id="excel-add-10-row-btn">10행 추가</button>
      <button type="button" id="excel-save-btn">전체 저장</button>
      <span id="excel-save-status"></span>
    </div>

    <div class="excel-summary-bar">
      <span>방문 카운트: <strong id="excel-visit-count">0</strong>명</span>
      <span>총매출: <strong id="excel-total-sales">0원</strong></span>
      <span>환불: <strong id="excel-total-refund">0원</strong></span>
      <span>저장 가능 행: <strong id="excel-valid-row-count">0</strong>개</span>
    </div>

    <div class="excel-table-wrap">
      <table class="customer-excel-table" id="customer-excel-table">
        <thead>
          <tr>
            <th>날짜</th>
            <th>고객구분</th>
            <th>성별</th>
            <th>고객명</th>
            <th>카드</th>
            <th>현금</th>
            <th>계좌이체</th>
            <th>충전금 사용</th>
            <th>환불</th>
            <th>비고</th>
            <th>삭제</th>
          </tr>
        </thead>
        <tbody id="customer-excel-body"></tbody>
      </table>
    </div>

    <script>
    (function () {
      const body = document.getElementById("customer-excel-body");
      const addRowBtn = document.getElementById("excel-add-row-btn");
      const add10RowBtn = document.getElementById("excel-add-10-row-btn");
      const saveBtn = document.getElementById("excel-save-btn");
      const statusEl = document.getElementById("excel-save-status");

      function todayText() {
        const d = new Date();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
      }

      function moneyToNumber(value) {
        if (value === undefined || value === null) return 0;
        const cleaned = String(value).replaceAll(",", "").replace(/[^0-9.-]/g, "");
        const n = Number(cleaned);
        return Number.isFinite(n) ? n : 0;
      }

      function formatWon(value) {
        return Number(value || 0).toLocaleString("ko-KR") + "원";
      }

      function handleGridNavigation(e) {
        const isSelect = e.target.tagName === "SELECT";
        if ((e.key === "ArrowDown" || e.key === "ArrowUp") && isSelect) return;

        const isVert  = e.key === "Enter" || e.key === "ArrowDown" || e.key === "ArrowUp";
        const isRight = e.key === "ArrowRight" || (e.key === "Tab" && !e.shiftKey);
        const isLeft  = e.key === "ArrowLeft"  || (e.key === "Tab" && e.shiftKey);
        if (!isVert && !isRight && !isLeft) return;

        const td = e.target.closest("td");
        const tr = td && td.closest("tr");
        if (!td || !tr) return;

        e.preventDefault();

        const colIndex = td.cellIndex;
        const MAX_COL  = 9;

        if (isRight) {
          if (colIndex < MAX_COL) {
            const f = tr.cells[colIndex + 1]?.querySelector("input, select");
            if (f) f.focus();
          } else {
            let nextRow = tr.nextElementSibling;
            if (!nextRow) { addRows(1); nextRow = body.lastElementChild; }
            const f = nextRow?.cells[0]?.querySelector("input, select");
            if (f) f.focus();
          }
          return;
        }

        if (isLeft) {
          if (colIndex > 0) {
            const f = tr.cells[colIndex - 1]?.querySelector("input, select");
            if (f) f.focus();
          } else {
            const prevRow = tr.previousElementSibling;
            const f = prevRow?.cells[MAX_COL]?.querySelector("input, select");
            if (f) f.focus();
          }
          return;
        }

        let targetRow;
        if (e.key === "Enter" || e.key === "ArrowDown") {
          targetRow = tr.nextElementSibling;
          if (!targetRow) { addRows(1); targetRow = body.lastElementChild; }
        } else {
          targetRow = tr.previousElementSibling;
        }

        if (!targetRow) return;
        const focusable = targetRow.cells[colIndex]?.querySelector("input, select");
        if (focusable) focusable.focus();
      }

      function makeRow() {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><input type="date" class="cell-date"></td>
          <td>
            <select class="cell-customer-type">
              <option value="">선택</option>
              <option value="신환">신환</option>
              <option value="구환">구환</option>
            </select>
          </td>
          <td>
            <select class="cell-gender">
              <option value="">선택</option>
              <option value="여">여</option>
              <option value="남">남</option>
            </select>
          </td>
          <td><input type="text" class="cell-name" placeholder="고객명"></td>
          <td><input type="text" inputmode="numeric" class="cell-card amount-cell" placeholder="0"></td>
          <td><input type="text" inputmode="numeric" class="cell-cash amount-cell" placeholder="0"></td>
          <td><input type="text" inputmode="numeric" class="cell-transfer amount-cell" placeholder="0"></td>
          <td><input type="text" inputmode="numeric" class="cell-prepaid amount-cell" placeholder="0"></td>
          <td><input type="text" inputmode="numeric" class="cell-refund amount-cell refund-cell" placeholder="0"></td>
          <td><input type="text" class="cell-memo" placeholder="비고"></td>
          <td><button type="button" class="row-delete-btn" tabindex="-1">×</button></td>
        `;

        tr.querySelector(".cell-name").addEventListener("input", function () {
          const dateInput = tr.querySelector(".cell-date");
          if (this.value.trim() && !dateInput.value) {
            dateInput.value = todayText();
          }
          updateSummary();
        });

        tr.querySelectorAll("input, select").forEach((el) => {
          el.addEventListener("input", updateSummary);
          el.addEventListener("change", updateSummary);
          el.addEventListener("keydown", handleGridNavigation);
        });

        tr.querySelector(".row-delete-btn").addEventListener("click", function () {
          tr.remove();
          if (body.children.length === 0) {
            addRows(1);
          }
          updateSummary();
        });

        return tr;
      }

      function addRows(count) {
        for (let i = 0; i < count; i++) {
          body.appendChild(makeRow());
        }
        updateSummary();
      }

      function getRowData(tr) {
        const date = tr.querySelector(".cell-date").value;
        const customerType = tr.querySelector(".cell-customer-type").value;
        const gender = tr.querySelector(".cell-gender").value;
        const name = tr.querySelector(".cell-name").value.trim();
        const card = moneyToNumber(tr.querySelector(".cell-card").value);
        const cash = moneyToNumber(tr.querySelector(".cell-cash").value);
        const transfer = moneyToNumber(tr.querySelector(".cell-transfer").value);
        const prepaid = moneyToNumber(tr.querySelector(".cell-prepaid").value);
        const refund = moneyToNumber(tr.querySelector(".cell-refund").value);
        const memo = tr.querySelector(".cell-memo").value.trim();
        const paymentTotal = card + cash + transfer;
        const netSales = paymentTotal - refund;
        const isRefund = refund > 0;
        const isEmpty = !date && !name && paymentTotal === 0 && prepaid === 0 && refund === 0 && !memo;

        return {
          date,
          customer_type: customerType,
          gender,
          customer_name: name,
          card,
          cash,
          transfer,
          prepaid,
          refund,
          memo,
          payment_total: paymentTotal,
          net_sales: netSales,
          is_refund: isRefund,
          is_empty: isEmpty
        };
      }

      function validateRows() {
        const rows = Array.from(body.querySelectorAll("tr"));
        const data = [];
        const errors = [];

        rows.forEach((tr, index) => {
          tr.classList.remove("row-error");
          const row = getRowData(tr);
          if (row.is_empty) return;

          if (!row.date) {
            errors.push(`${index + 1}행: 날짜가 필요합니다.`);
            tr.classList.add("row-error");
          }

          if (!row.customer_name && row.refund <= 0) {
            errors.push(`${index + 1}행: 고객명이 필요합니다.`);
            tr.classList.add("row-error");
          }

          if (row.payment_total <= 0 && row.prepaid <= 0 && row.refund <= 0) {
            errors.push(`${index + 1}행: 결제금액, 충전금 사용, 환불금액 중 하나가 필요합니다.`);
            tr.classList.add("row-error");
          }

          if (row.refund > 0 && (row.payment_total > 0 || row.prepaid > 0)) {
            errors.push(`${index + 1}행: 환불 행에는 카드/현금/계좌이체/충전금 사용 금액을 같이 입력하지 마세요.`);
            tr.classList.add("row-error");
          }

          data.push(row);
        });

        return { data, errors };
      }

      function updateSummary() {
        const rows = Array.from(body.querySelectorAll("tr")).map(getRowData).filter(row => !row.is_empty);
        let visitCount = 0;
        let totalSales = 0;
        let totalRefund = 0;
        let validRows = 0;

        rows.forEach((row) => {
          totalSales += row.net_sales;
          totalRefund += row.refund;
          if (!row.is_refund) {
            visitCount += 1;
          }
          if (row.date && (row.payment_total > 0 || row.prepaid > 0 || row.refund > 0)) {
            validRows += 1;
          }
        });

        document.getElementById("excel-visit-count").textContent = visitCount.toLocaleString("ko-KR");
        document.getElementById("excel-total-sales").textContent = formatWon(totalSales);
        document.getElementById("excel-total-refund").textContent = formatWon(totalRefund);
        document.getElementById("excel-valid-row-count").textContent = validRows.toLocaleString("ko-KR");
      }

      async function saveRows() {
        const result = validateRows();

        if (result.errors.length > 0) {
          statusEl.textContent = result.errors[0];
          statusEl.className = "status-error";
          alert(result.errors.join("\\n"));
          return;
        }

        if (result.data.length === 0) {
          statusEl.textContent = "저장할 행이 없습니다.";
          statusEl.className = "status-error";
          return;
        }

        saveBtn.disabled = true;
        statusEl.textContent = "저장 중...";
        statusEl.className = "";

        try {
          const response = await fetch("/api/customers/excel-bulk-save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rows: result.data })
          });

          const data = await response.json();

          if (!response.ok || data.ok === false) {
            throw new Error(data.error || "저장 실패");
          }

          statusEl.textContent = `${data.saved_count}개 행 저장 완료`;
          statusEl.className = "status-success";
          body.innerHTML = "";
          addRows(10);

        } catch (error) {
          console.error(error);
          statusEl.textContent = error.message || "저장 중 오류가 발생했습니다.";
          statusEl.className = "status-error";
        } finally {
          saveBtn.disabled = false;
        }
      }

      addRowBtn.addEventListener("click", function () { addRows(1); });
      add10RowBtn.addEventListener("click", function () { addRows(10); });
      saveBtn.addEventListener("click", saveRows);

      addRows(10);
    })();
    </script>
    {% endblock %}
    """

    return render_template_string(html)

@app.route("/api/customers/excel-bulk-save", methods=["POST"])
def api_customer_excel_bulk_save():
    from flask import request, jsonify
    import sqlite3
    from datetime import datetime

    DB_PATH = "beauty_app.db"
    WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

    payload = request.get_json(silent=True) or {}
    rows = payload.get("rows", [])

    if not isinstance(rows, list) or not rows:
        return jsonify({"ok": False, "error": "저장할 데이터가 없습니다."}), 400

    def to_int(value):
        try:
            if value is None or value == "":
                return 0
            return int(float(str(value).replace(",", "")))
        except Exception:
            return 0

    def clean_text(value):
        return str(value or "").strip()

    cleaned_rows = []
    errors = []

    for idx, row in enumerate(rows, start=1):
        date_text = clean_text(row.get("date"))
        customer_name = clean_text(row.get("customer_name"))
        customer_type = clean_text(row.get("customer_type"))
        gender = clean_text(row.get("gender"))
        memo = clean_text(row.get("memo"))

        card = to_int(row.get("card"))
        cash = to_int(row.get("cash"))
        transfer = to_int(row.get("transfer"))
        prepaid_usage = to_int(row.get("prepaid") if row.get("prepaid") is not None else row.get("prepaid_usage"))
        refund = to_int(row.get("refund"))

        try:
            date_obj = datetime.strptime(date_text, "%Y-%m-%d").date()
        except Exception:
            errors.append(f"{idx}행: 날짜 형식이 올바르지 않습니다.")
            continue

        # 충전금 사용은 매출에 포함하지 않는다.
        # 총매출 = 카드 + 현금 + 계좌이체 - 환불
        payment_total = card + cash + transfer
        net_sales = payment_total - refund
        is_refund = 1 if refund > 0 else 0

        if not customer_name and refund <= 0:
            errors.append(f"{idx}행: 고객명이 필요합니다.")
            continue

        if payment_total <= 0 and prepaid_usage <= 0 and refund <= 0:
            errors.append(f"{idx}행: 결제금액, 충전금 사용, 환불금액 중 하나가 필요합니다.")
            continue

        if refund > 0 and (payment_total > 0 or prepaid_usage > 0):
            errors.append(f"{idx}행: 환불 행에는 카드/현금/계좌이체/충전금 사용 금액을 같이 입력할 수 없습니다.")
            continue

        cleaned_rows.append({
            "date": date_obj.isoformat(),
            "year": date_obj.year,
            "month": date_obj.month,
            "day": date_obj.day,
            "weekday": WEEKDAY_KO[date_obj.weekday()],
            "is_workday": 0 if date_obj.weekday() == 6 else 1,
            "customer_name": customer_name,
            "customer_type": customer_type,
            "gender": gender,
            "card": card,
            "cash": cash,
            "transfer": transfer,
            "prepaid_usage": prepaid_usage,
            "refund": refund,
            "memo": memo,
            "payment_total": payment_total,
            "net_sales": net_sales,
            "is_refund": is_refund
        })

    if errors:
        return jsonify({"ok": False, "error": "\n".join(errors)}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_excel_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                customer_type TEXT,
                gender TEXT,
                customer_name TEXT,
                card INTEGER DEFAULT 0,
                cash INTEGER DEFAULT 0,
                transfer INTEGER DEFAULT 0,
                prepaid INTEGER DEFAULT 0,
                refund INTEGER DEFAULT 0,
                memo TEXT,
                net_sales INTEGER DEFAULT 0,
                is_refund INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS prepaid_usage_daily_summary (
                date TEXT PRIMARY KEY,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                weekday TEXT,
                prepaid_usage_total INTEGER DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for row in cleaned_rows:
            conn.execute("""
                INSERT INTO customer_excel_entries
                (date, customer_type, gender, customer_name, card, cash, transfer, prepaid, refund, memo, net_sales, is_refund)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["date"], row["customer_type"], row["gender"], row["customer_name"],
                row["card"], row["cash"], row["transfer"], row["prepaid_usage"], row["refund"],
                row["memo"], row["net_sales"], row["is_refund"]
            ))

            if row["prepaid_usage"] > 0 and row["is_refund"] == 0:
                conn.execute("""
                    INSERT INTO prepaid_usage_entries
                    (date, customer_name, customer_type, gender, prepaid_usage, memo, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["date"], row["customer_name"], row["customer_type"], row["gender"],
                    row["prepaid_usage"], row["memo"], "customer_excel"
                ))

        affected_dates = sorted(set(row["date"] for row in cleaned_rows))

        for date_text in affected_dates:
            day_rows = [row for row in cleaned_rows if row["date"] == date_text]
            first = day_rows[0]

            visit_count = sum(1 for row in day_rows if row["is_refund"] == 0)

            new_sales = sum(
                row["net_sales"]
                for row in day_rows
                if row["is_refund"] == 0 and row["customer_type"] == "신환"
            )

            returning_sales = sum(
                row["net_sales"]
                for row in day_rows
                if row["is_refund"] == 0 and row["customer_type"] == "구환"
            )

            total_sales = sum(row["net_sales"] for row in day_rows)

            prepaid_usage_total = sum(
                row["prepaid_usage"]
                for row in day_rows
                if row["is_refund"] == 0
            )

            prepaid_usage_count = sum(
                1
                for row in day_rows
                if row["is_refund"] == 0 and row["prepaid_usage"] > 0
            )

            conn.execute("""
                INSERT INTO prepaid_usage_daily_summary
                (date, year, month, day, weekday, prepaid_usage_total, usage_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    prepaid_usage_total = COALESCE(prepaid_usage_total, 0) + excluded.prepaid_usage_total,
                    usage_count = COALESCE(usage_count, 0) + excluded.usage_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                date_text, first["year"], first["month"], first["day"], first["weekday"],
                prepaid_usage_total, prepaid_usage_count
            ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500

    conn.close()

    for date_text in affected_dates:
        recalculate_summary(date_text)

    return jsonify({
        "ok": True,
        "saved_count": len(cleaned_rows),
        "affected_dates": affected_dates,
        "note": "충전금 사용은 매출에 포함하지 않고 별도 관리되었습니다."
    })
# 충전금 사용 분리 v3 패치 적용됨

#

# -------------------------------------------------------------------
# 고객입력 엑셀형 개편 3단계
# GET /api/customers/excel-list
# - 날짜 범위별 엑셀형 고객입력 데이터 조회
# -------------------------------------------------------------------
@app.route("/api/customers/excel-list", methods=["GET"])
def api_customers_excel_list():
    from flask import request, jsonify
    from datetime import date, datetime
    import sqlite3

    DB_PATH = "beauty_app.db"

    today_text = date.today().isoformat()
    start_text = request.args.get("start") or today_text
    end_text = request.args.get("end") or today_text

    try:
        start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
    except Exception:
        return jsonify({
            "ok": False,
            "error": "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 요청하세요."
        }), 400

    if start_date > end_date:
        return jsonify({
            "ok": False,
            "error": "시작일이 종료일보다 늦을 수 없습니다."
        }), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("""
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

        db_rows = conn.execute("""
            SELECT
                id,
                date,
                customer_type,
                gender,
                customer_name,
                COALESCE(card, 0) AS card,
                COALESCE(cash, 0) AS cash,
                COALESCE(transfer, 0) AS transfer,
                COALESCE(refund, 0) AS refund,
                COALESCE(prepaid, 0) AS prepaid,
                memo,
                COALESCE(net_sales, 0) AS net_sales,
                COALESCE(is_refund, 0) AS is_refund,
                created_by,
                created_at,
                updated_by,
                updated_at
            FROM customer_excel_entries
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC, id DESC
        """, (start_date.isoformat(), end_date.isoformat())).fetchall()

    except Exception as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500

    conn.close()

    rows = []
    total_sales = 0
    total_refund = 0
    total_prepaid = 0
    visit_count = 0

    for r in db_rows:
        row = dict(r)
        row["is_refund"] = bool(row.get("is_refund"))

        total_sales += int(row.get("net_sales") or 0)
        total_refund += int(row.get("refund") or 0)
        total_prepaid += int(row.get("prepaid") or 0)

        if not row["is_refund"]:
            visit_count += 1

        rows.append(row)

    return jsonify({
        "ok": True,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "count": len(rows),
        "summary": {
            "visit_count": visit_count,
            "total_sales": total_sales,
            "total_refund": total_refund,
            "total_prepaid": total_prepaid
        },
        "rows": rows
    })

@app.route('/api/analytics/period-summary')
def api_period_summary():
    """기간별 집계 API — daily_closing_summary 테이블에서 집계"""
    import sqlite3
    from datetime import date, datetime

    DB_PATH = 'beauty_app.db'
    VALID_UNITS = ['day', 'week', 'month', 'quarter', 'half', 'year']
    WEEKDAY_KO = ['월', '화', '수', '목', '금', '토', '일']

    unit = request.args.get('unit', 'day')
    start_text = request.args.get('start')
    end_text = request.args.get('end')

    if unit not in VALID_UNITS:
        return jsonify({
            'ok': False,
            'error': '지원하지 않는 기간 단위입니다.',
            'allowed_units': VALID_UNITS
        }), 400

    if not start_text or not end_text:
        return jsonify({
            'ok': False,
            'error': 'start와 end는 필수입니다. 형식은 YYYY-MM-DD입니다.'
        }), 400

    try:
        start_date = datetime.strptime(start_text, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_text, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'ok': False,
            'error': '날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요.'
        }), 400

    if start_date > end_date:
        return jsonify({
            'ok': False,
            'error': '시작일이 종료일보다 늦을 수 없습니다.'
        }), 400

    def make_period_label(unit_name, start_d, end_d):
        if unit_name == 'day':
            weekday = WEEKDAY_KO[start_d.weekday()]
            return f'{start_d.isoformat()} ({weekday})'

        if unit_name == 'week':
            iso_week = start_d.isocalendar()[1]
            return f'{start_d.year}년 {iso_week}주차 ({start_d.month}/{start_d.day}~{end_d.month}/{end_d.day})'

        if unit_name == 'month':
            return f'{start_d.year}년 {start_d.month}월'

        if unit_name == 'quarter':
            quarter = ((start_d.month - 1) // 3) + 1
            quarter_start_month = (quarter - 1) * 3 + 1
            quarter_end_month = quarter_start_month + 2
            return f'{start_d.year}년 {quarter}Q ({quarter_start_month}~{quarter_end_month}월)'

        if unit_name == 'half':
            if start_d.month <= 6:
                return f'{start_d.year}년 상반기'
            return f'{start_d.year}년 하반기'

        if unit_name == 'year':
            return f'{start_d.year}년'

        return f'{start_d.isoformat()} ~ {end_d.isoformat()}'

    today = date.today()
    is_current = start_date <= today <= end_date

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                COALESCE(SUM(total_visit_count), 0) AS total_visit,
                COALESCE(SUM(new_customer_sales), 0) AS new_customer_sales,
                COALESCE(SUM(returning_customer_sales), 0) AS returning_customer_sales,
                COALESCE(SUM(total_daily_sales), 0) AS total_sales,
                COALESCE(SUM(total_expense), 0) AS total_expense,
                COALESCE(SUM(CASE WHEN is_workday = 1 THEN 1 ELSE 0 END), 0) AS workday_count
            FROM daily_closing_summary
            WHERE date BETWEEN ? AND ?
            """,
            (start_date.isoformat(), end_date.isoformat())
        ).fetchone()
    except sqlite3.OperationalError as e:
        conn.close()
        return jsonify({
            'ok': False,
            'error': 'daily_closing_summary 테이블 또는 필요한 컬럼을 찾을 수 없습니다.',
            'detail': str(e)
        }), 500

    conn.close()

    total_visit = int(row['total_visit'] or 0)
    new_customer_sales = int(row['new_customer_sales'] or 0)
    returning_customer_sales = int(row['returning_customer_sales'] or 0)
    total_sales = int(row['total_sales'] or 0)
    total_expense = int(row['total_expense'] or 0)
    workday_count = int(row['workday_count'] or 0)
    closing = total_sales - total_expense

    has_data = not (
        total_visit == 0 and
        new_customer_sales == 0 and
        returning_customer_sales == 0 and
        total_sales == 0 and
        total_expense == 0 and
        workday_count == 0
    )

    label = make_period_label(unit, start_date, end_date)

    return jsonify({
        'ok': True,
        'unit': unit,
        'start': start_date.isoformat(),
        'end': end_date.isoformat(),
        'label': label,
        'is_current': is_current,
        'has_data': has_data,
        'total_visit': total_visit,
        'new_customer_sales': new_customer_sales,
        'returning_customer_sales': returning_customer_sales,
        'total_sales': total_sales,
        'total_expense': total_expense,
        'closing': closing,
        'workday_count': workday_count
    })


if __name__ == '__main__':
    init_db(); app.run(debug=True, host='127.0.0.1', port=5000)



# -------------------------------------------------------------------
# 결산분석 요약 API v2
# 요약 카드 2열 UI + 지난달 동일 요일 평균 비교
# -------------------------------------------------------------------


