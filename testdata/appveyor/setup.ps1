
$params = @($env:BROKER, $env:RESULT, $env:LOCK)
if ($params -contains 'mysql')
{
    & mysql -u root -p"Password12!" -e "CREATE DATABASE flask_celery_helper_test;"
    & mysql -u root -p"Password12!" -e "GRANT ALL PRIVILEGES ON flask_celery_helper_test.* TO 'user'@'localhost' IDENTIFIED BY 'pass';"
}

if ($params -contains 'postgres')
{
    & psql -U postgres -c "CREATE DATABASE flask_celery_helper_test;"
    & psql -U postgres -c "CREATE USER user1 WITH PASSWORD 'pass';"
    & psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE flask_celery_helper_test TO user1;"
}

if ($params -contains 'redis')
{
    cinst redis-64
    redis-server --service-install
    redis-server --service-start
}

if ($params -contains 'rabbit')
{
    & "install-rabbitmq.ps1"
}