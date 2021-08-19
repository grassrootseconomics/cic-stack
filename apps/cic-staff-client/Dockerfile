# defining version of the base image
FROM node:alpine as build

RUN apk add --no-cache bash

# defining work directory
WORKDIR /app

# copying the json files into the image
COPY package*.json .
COPY patch-webpack.js .

# copying rest of project
RUN --mount=type=cache,id=npm,target=/app/.npm \
    npm set cache /app/.npm && \
    npm ci

COPY . .

ARG FRONTEND_ENV=prod
# running build script
RUN npm run build:${FRONTEND_ENV}

### STAGE 2: Setup ###
# defining nginx image version
FROM nginx:alpine as server

## Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# copy dist output from our first image
COPY --from=build /app/dist/cic-staff-client /usr/share/nginx/html

# copy nginx configuration file
COPY nginx.conf /etc/nginx/

EXPOSE 80

CMD [ "nginx", "-g", "daemon off;" ]
