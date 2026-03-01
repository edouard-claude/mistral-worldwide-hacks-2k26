FROM node:22-alpine

WORKDIR /app

COPY . .

RUN mkdir -p data

ENV PORT=3000
ENV REFRESH_INTERVAL=30

EXPOSE 3000

CMD ["node", "server.mjs"]
