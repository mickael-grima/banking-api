container_id="$(docker ps -q -f name=mysqldb)"

user="root"
password="password"
dbname="banking-api"

query="TRUNCATE TABLE accounts;
TRUNCATE TABLE transfers;
TRUNCATE TABLE customers;
"

docker exec "$container_id" mysql -u"$user" -p"$password" -e "$query" "$dbname"