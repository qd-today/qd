# Update

> Please always remember to back up your database before updating or redeploying.
>
> After the update, please restart the container or clear the browser cache.

## Source Code Deployment Update

   ``` sh
   # First cd to the directory of source code, execute the command and restart the process
   wget https://gitee.com/qd-today/qd/raw/master/update.sh -O ./update.sh && \
   sh ./update.sh
   ```

## Docker Compose Deployment Update

   ``` sh
   # First cd to the directory of docker-compose.yml, execute the command and restart the container
   docker compose pull && \
   docker compose up -d
   ```

## Docker Container Deployment Update

   ``` sh
   # Enter the container background first, restart the container after executing the command
   wget https://gitee.com/qd-today/qd/raw/master/update.sh -O /usr/src/app/update.sh && \
   sh /usr/src/app/update.sh
   ```

## Forcibly synchronize the latest source code

   ``` sh
   # First cd to the root directory of code, execute the command and restart the process
   # docker exec -it "container name" /bin/sh
   wget https://gitee.com/qd-today/qd/raw/master/update.sh -O ./update.sh && \
   sh ./update.sh -f
   ```
