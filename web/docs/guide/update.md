# Update

> Please always remember to back up your database before updating or redeploying.
>
> After the update, please restart the container or clear the browser cache.

## Source Code Deployment Update

   ``` sh
   # First cd to the directory of source code, execute the command and restart the process
   wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O ./update.sh && \
   sh ./update.sh
   ```

## Docker Container Deployment Update

   ``` sh
   # Enter the container background first, restart the container after executing the command
   wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O /usr/src/app/update.sh && \
   sh /usr/src/app/update.sh
   ```

## Forcibly synchronize the latest source code

   ``` sh
   # First cd to the root directory of code, execute the command and restart the process
   wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O ./update.sh && \
   sh ./update.sh -f
   ```
