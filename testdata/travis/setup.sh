#!/bin/bash

setup_mysql () {
    mysql -u root -e 'CREATE DATABASE flask_celery_helper_test;'
    mysql -u root -e 'GRANT ALL PRIVILEGES ON flask_celery_helper_test.* TO "user"@"localhost" IDENTIFIED BY "pass";'
}

setup_postgres () {
    psql -U postgres -c 'CREATE DATABASE flask_celery_helper_test;'
    psql -U postgres -c "CREATE USER user1 WITH PASSWORD 'pass';"
    psql -U postgres -c 'GRANT ALL PRIVILEGES ON DATABASE flask_celery_helper_test TO user1;'
}

setup_redis_sock () {
    echo -e "daemonize yes\\nunixsocket /tmp/redis.sock\\nport 0" |redis-server -
}

setup_rabbit_vhost () {
    rabbitmqctl add_vhost travis_vhost_${TRAVIS_JOB_ID}
    rabbitmqctl set_permissions -p travis_vhost_${TRAVIS_JOB_ID} guest ".*" ".*" ".*"
}

if [ "$BROKER" == mysql ] || [ "$RESULT" == mysql ] || [ "$LOCK" == mysql ]; then
    setup_mysql
fi

if [ "$BROKER" == postgres ] || [ "$RESULT" == postgres ] || [ "$LOCK" == postgres ]; then
    setup_postgres
fi

if [[ "$BROKER" == redis_sock* ]] || [[ "$RESULT" == redis_sock* ]] || [[ "$LOCK" == redis_sock* ]]; then
    setup_redis_sock
fi

if [[ "$BROKER" == rabbit ]] || [[ "$RESULT" == rabbit ]] || [[ "$LOCK" == rabbit ]]; then
    setup_rabbit_vhost
fi