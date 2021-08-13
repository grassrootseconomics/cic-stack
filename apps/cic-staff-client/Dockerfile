# defining version of the base image
FROM node:alpine as build

# defining work directory
WORKDIR /app

# copying the json files into the image
COPY package*.json .
COPY patch-webpack.js .

RUN npm install
# copying rest of project

COPY . .

ARG FRONTEND_ENV="production"

# running build script
RUN npm run build:${FRONTEND_ENV}

### STAGE 2: Setup ###
# defining nginx image version
FROM nginx:alpine

## Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# copy dist output from our first image
COPY --from=build /app/dist/cic-staff-client /usr/share/nginx/html

# copy nginx configuration file
COPY nginx.conf /etc/nginx/

EXPOSE 80

CMD [ "nginx", "-g", "daemon off;" ]
