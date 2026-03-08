# Docker 針對不同作業系統有特定的安裝指示。
# 請至 https://docker.com/get-started/ 查閱官方文件
# 拉取 Node.js Docker 映像：
docker pull node:25-alpine
# 建立 Node.js 容器並啟動 Shell 工作階段：
docker run -it --rm --entrypoint sh node:25-alpine
# Verify the Node.js version:
node -v # Should print "v25.7.0".
# 核對 npm 版本：
npm -v # 應會印出 "11.10.1"。