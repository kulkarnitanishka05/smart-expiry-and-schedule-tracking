from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date
from models import db, Item, Alert
from config import ALERT_DAYS

def _make_alert(item: Item, days_left: int):
    msg = f"{item.name} expires in {days_left} day(s) on {item.expiry_date.isoformat()}"
    # avoid duplicate alert for same item+date
    existing = Alert.query.filter_by(item_id=item.id, message=msg, resolved=False).first()
    if not existing:
        db.session.add(Alert(item_id=item.id, message=msg))
        db.session.commit()

def check_expiries():
    today = date.today()
    items = Item.query.all()
    for it in items:
        dl = (it.expiry_date - today).days
        if dl <= ALERT_DAYS:
            _make_alert(it, dl)

def start_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    def _job():
        with app.app_context():
            check_expiries()
    scheduler.add_job(func=_job, trigger="interval", seconds=60)  # every 60s
    scheduler.start()
    return scheduler
