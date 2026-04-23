$env:FLASK_APP="manage.py"

psql -U postgres -d postgres
CREATE DATABASE lichhoc;

flask db init      # nếu chưa có thư mục migrations
flask db migrate -m "Initial migration"
flask db upgrade
