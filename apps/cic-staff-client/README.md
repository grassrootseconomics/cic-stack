# CICADA

An angular admin web client for managing users and transactions in the CIC network.

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 10.2.0.

## Angular CLI

Run `npm install -g @angular/cli` to install the angular CLI.

## Development server

Run  `ng serve` for a local server, `npm run start:dev` for a dev server and  `npm run start:prod` for a prod server..

Navigate to `http://localhost:4200/`. The app will automatically reload if you change any of the source files.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Lazy-loading feature modules

Run `ng generate module module-name --route module-name --module app.module` to generate a new module on route `/module-name` in the app module. 

## Build

Run `ng build` to build the project using local configurations.
The build artifacts will be stored in the `dist/` directory.

Use the `npm run build:dev` script for a development build and the `npm run build:prod` script for a production build.

## PWA

The app supports Progressive Web App capabilities.

Run `npm run start:pwa` to run the project in PWA mode.
PWA mode works using production configurations.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via [Protractor](http://www.protractortest.org/).

## Environment variables

Default environment variables are located in the `src/environments/` directory.
Custom environment variables are contained in the `.env` file. See `.env.example` for a template.

Custom environment variables are set via the `set-env.ts` file.
Once loaded they will be populated in the directory `src/environments/`.
It contains environment variables for development on `environment.dev.ts` and production on `environment.prod.ts`.

## Code formatting

The system has automated code formatting using [Prettier](https://prettier.io/) and [TsLint](https://palantir.github.io/tslint/).
To view the styling rules set, check out `.prettierrc` and `tslint.json`.

Run `npm run format:lint` To perform formatting and linting of the codebase.

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI Overview and Command Reference](https://angular.io/cli) page.
