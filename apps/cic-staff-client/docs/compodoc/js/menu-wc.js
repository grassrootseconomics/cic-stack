'use strict';


customElements.define('compodoc-menu', class extends HTMLElement {
    constructor() {
        super();
        this.isNormalMode = this.getAttribute('mode') === 'normal';
    }

    connectedCallback() {
        this.render(this.isNormalMode);
    }

    render(isNormalMode) {
        let tp = lithtml.html(`
        <nav>
            <ul class="list">
                <li class="title">
                    <a href="index.html" data-type="index-link">CICADA</a>
                </li>

                <li class="divider"></li>
                ${ isNormalMode ? `<div id="book-search-input" role="search"><input type="text" placeholder="Type to search"></div>` : '' }
                <li class="chapter">
                    <a data-type="chapter-link" href="index.html"><span class="icon ion-ios-home"></span>Getting started</a>
                    <ul class="links">
                        <li class="link">
                            <a href="overview.html" data-type="chapter-link">
                                <span class="icon ion-ios-keypad"></span>Overview
                            </a>
                        </li>
                        <li class="link">
                            <a href="index.html" data-type="chapter-link">
                                <span class="icon ion-ios-paper"></span>README
                            </a>
                        </li>
                        <li class="link">
                            <a href="license.html"  data-type="chapter-link">
                                <span class="icon ion-ios-paper"></span>LICENSE
                            </a>
                        </li>
                                <li class="link">
                                    <a href="dependencies.html" data-type="chapter-link">
                                        <span class="icon ion-ios-list"></span>Dependencies
                                    </a>
                                </li>
                    </ul>
                </li>
                    <li class="chapter modules">
                        <a data-type="chapter-link" href="modules.html">
                            <div class="menu-toggler linked" data-toggle="collapse" ${ isNormalMode ?
                                'data-target="#modules-links"' : 'data-target="#xs-modules-links"' }>
                                <span class="icon ion-ios-archive"></span>
                                <span class="link-name">Modules</span>
                                <span class="icon ion-ios-arrow-down"></span>
                            </div>
                        </a>
                        <ul class="links collapse " ${ isNormalMode ? 'id="modules-links"' : 'id="xs-modules-links"' }>
                            <li class="link">
                                <a href="modules/AccountsModule.html" data-type="entity-link">AccountsModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-AccountsModule-1a1e33fcf3e34d5cc3aaa35d56c0aa4c"' : 'data-target="#xs-components-links-module-AccountsModule-1a1e33fcf3e34d5cc3aaa35d56c0aa4c"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-AccountsModule-1a1e33fcf3e34d5cc3aaa35d56c0aa4c"' :
                                            'id="xs-components-links-module-AccountsModule-1a1e33fcf3e34d5cc3aaa35d56c0aa4c"' }>
                                            <li class="link">
                                                <a href="components/AccountDetailsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AccountDetailsComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/AccountSearchComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AccountSearchComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/AccountsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AccountsComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/CreateAccountComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">CreateAccountComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/AccountsRoutingModule.html" data-type="entity-link">AccountsRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/AdminModule.html" data-type="entity-link">AdminModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-AdminModule-bf625bdb8aefe13672d7b39813a7c308"' : 'data-target="#xs-components-links-module-AdminModule-bf625bdb8aefe13672d7b39813a7c308"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-AdminModule-bf625bdb8aefe13672d7b39813a7c308"' :
                                            'id="xs-components-links-module-AdminModule-bf625bdb8aefe13672d7b39813a7c308"' }>
                                            <li class="link">
                                                <a href="components/AdminComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AdminComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/AdminRoutingModule.html" data-type="entity-link">AdminRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/AppModule.html" data-type="entity-link">AppModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' : 'data-target="#xs-components-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' :
                                            'id="xs-components-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' }>
                                            <li class="link">
                                                <a href="components/AppComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AppComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                                <li class="chapter inner">
                                    <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                        'data-target="#injectables-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' : 'data-target="#xs-injectables-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' }>
                                        <span class="icon ion-md-arrow-round-down"></span>
                                        <span>Injectables</span>
                                        <span class="icon ion-ios-arrow-down"></span>
                                    </div>
                                    <ul class="links collapse" ${ isNormalMode ? 'id="injectables-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' :
                                        'id="xs-injectables-links-module-AppModule-76194cd3efb2efcb11dc0e91210acb63"' }>
                                        <li class="link">
                                            <a href="injectables/GlobalErrorHandler.html"
                                                data-type="entity-link" data-context="sub-entity" data-context-id="modules" }>GlobalErrorHandler</a>
                                        </li>
                                    </ul>
                                </li>
                            </li>
                            <li class="link">
                                <a href="modules/AppRoutingModule.html" data-type="entity-link">AppRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/AuthModule.html" data-type="entity-link">AuthModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' : 'data-target="#xs-components-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' :
                                            'id="xs-components-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' }>
                                            <li class="link">
                                                <a href="components/AuthComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">AuthComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                                <li class="chapter inner">
                                    <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                        'data-target="#directives-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' : 'data-target="#xs-directives-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' }>
                                        <span class="icon ion-md-code-working"></span>
                                        <span>Directives</span>
                                        <span class="icon ion-ios-arrow-down"></span>
                                    </div>
                                    <ul class="links collapse" ${ isNormalMode ? 'id="directives-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' :
                                        'id="xs-directives-links-module-AuthModule-21adac75fe3c63a79af20c68295f3af3"' }>
                                        <li class="link">
                                            <a href="directives/PasswordToggleDirective.html"
                                                data-type="entity-link" data-context="sub-entity" data-context-id="modules">PasswordToggleDirective</a>
                                        </li>
                                    </ul>
                                </li>
                            </li>
                            <li class="link">
                                <a href="modules/AuthRoutingModule.html" data-type="entity-link">AuthRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/PagesModule.html" data-type="entity-link">PagesModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-PagesModule-4cd3582cec47ee4784a648a95d374033"' : 'data-target="#xs-components-links-module-PagesModule-4cd3582cec47ee4784a648a95d374033"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-PagesModule-4cd3582cec47ee4784a648a95d374033"' :
                                            'id="xs-components-links-module-PagesModule-4cd3582cec47ee4784a648a95d374033"' }>
                                            <li class="link">
                                                <a href="components/PagesComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">PagesComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/PagesRoutingModule.html" data-type="entity-link">PagesRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/SettingsModule.html" data-type="entity-link">SettingsModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-SettingsModule-5044f5da70b3cb7481119034e269a4c0"' : 'data-target="#xs-components-links-module-SettingsModule-5044f5da70b3cb7481119034e269a4c0"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-SettingsModule-5044f5da70b3cb7481119034e269a4c0"' :
                                            'id="xs-components-links-module-SettingsModule-5044f5da70b3cb7481119034e269a4c0"' }>
                                            <li class="link">
                                                <a href="components/OrganizationComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">OrganizationComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/SettingsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">SettingsComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/SettingsRoutingModule.html" data-type="entity-link">SettingsRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/SharedModule.html" data-type="entity-link">SharedModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' : 'data-target="#xs-components-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' :
                                            'id="xs-components-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                            <li class="link">
                                                <a href="components/ErrorDialogComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">ErrorDialogComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/FooterComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">FooterComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/NetworkStatusComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">NetworkStatusComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/SidebarComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">SidebarComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/TopbarComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TopbarComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                                <li class="chapter inner">
                                    <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                        'data-target="#directives-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' : 'data-target="#xs-directives-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                        <span class="icon ion-md-code-working"></span>
                                        <span>Directives</span>
                                        <span class="icon ion-ios-arrow-down"></span>
                                    </div>
                                    <ul class="links collapse" ${ isNormalMode ? 'id="directives-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' :
                                        'id="xs-directives-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                        <li class="link">
                                            <a href="directives/MenuSelectionDirective.html"
                                                data-type="entity-link" data-context="sub-entity" data-context-id="modules">MenuSelectionDirective</a>
                                        </li>
                                        <li class="link">
                                            <a href="directives/MenuToggleDirective.html"
                                                data-type="entity-link" data-context="sub-entity" data-context-id="modules">MenuToggleDirective</a>
                                        </li>
                                    </ul>
                                </li>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#pipes-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' : 'data-target="#xs-pipes-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                            <span class="icon ion-md-add"></span>
                                            <span>Pipes</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="pipes-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' :
                                            'id="xs-pipes-links-module-SharedModule-3e576a8c748d27f7146572ab7c6213b0"' }>
                                            <li class="link">
                                                <a href="pipes/SafePipe.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">SafePipe</a>
                                            </li>
                                            <li class="link">
                                                <a href="pipes/TokenRatioPipe.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TokenRatioPipe</a>
                                            </li>
                                            <li class="link">
                                                <a href="pipes/UnixDatePipe.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">UnixDatePipe</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/TokensModule.html" data-type="entity-link">TokensModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-TokensModule-4cd6c9f8281377a062841d33114ab4d6"' : 'data-target="#xs-components-links-module-TokensModule-4cd6c9f8281377a062841d33114ab4d6"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-TokensModule-4cd6c9f8281377a062841d33114ab4d6"' :
                                            'id="xs-components-links-module-TokensModule-4cd6c9f8281377a062841d33114ab4d6"' }>
                                            <li class="link">
                                                <a href="components/TokenDetailsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TokenDetailsComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/TokensComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TokensComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/TokensRoutingModule.html" data-type="entity-link">TokensRoutingModule</a>
                            </li>
                            <li class="link">
                                <a href="modules/TransactionsModule.html" data-type="entity-link">TransactionsModule</a>
                                    <li class="chapter inner">
                                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ?
                                            'data-target="#components-links-module-TransactionsModule-7e4ae7b28baa579581c11fbb444cc24a"' : 'data-target="#xs-components-links-module-TransactionsModule-7e4ae7b28baa579581c11fbb444cc24a"' }>
                                            <span class="icon ion-md-cog"></span>
                                            <span>Components</span>
                                            <span class="icon ion-ios-arrow-down"></span>
                                        </div>
                                        <ul class="links collapse" ${ isNormalMode ? 'id="components-links-module-TransactionsModule-7e4ae7b28baa579581c11fbb444cc24a"' :
                                            'id="xs-components-links-module-TransactionsModule-7e4ae7b28baa579581c11fbb444cc24a"' }>
                                            <li class="link">
                                                <a href="components/TransactionDetailsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TransactionDetailsComponent</a>
                                            </li>
                                            <li class="link">
                                                <a href="components/TransactionsComponent.html"
                                                    data-type="entity-link" data-context="sub-entity" data-context-id="modules">TransactionsComponent</a>
                                            </li>
                                        </ul>
                                    </li>
                            </li>
                            <li class="link">
                                <a href="modules/TransactionsRoutingModule.html" data-type="entity-link">TransactionsRoutingModule</a>
                            </li>
                </ul>
                </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#components-links"' :
                            'data-target="#xs-components-links"' }>
                            <span class="icon ion-md-cog"></span>
                            <span>Components</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="components-links"' : 'id="xs-components-links"' }>
                            <li class="link">
                                <a href="components/AccountDetailsComponent.html" data-type="entity-link">AccountDetailsComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/CreateAccountComponent.html" data-type="entity-link">CreateAccountComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/ErrorDialogComponent.html" data-type="entity-link">ErrorDialogComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/FooterComponent.html" data-type="entity-link">FooterComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/FooterStubComponent.html" data-type="entity-link">FooterStubComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/OrganizationComponent.html" data-type="entity-link">OrganizationComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/SidebarComponent.html" data-type="entity-link">SidebarComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/SidebarStubComponent.html" data-type="entity-link">SidebarStubComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/TokenDetailsComponent.html" data-type="entity-link">TokenDetailsComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/TopbarComponent.html" data-type="entity-link">TopbarComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/TopbarStubComponent.html" data-type="entity-link">TopbarStubComponent</a>
                            </li>
                            <li class="link">
                                <a href="components/TransactionDetailsComponent.html" data-type="entity-link">TransactionDetailsComponent</a>
                            </li>
                        </ul>
                    </li>
                        <li class="chapter">
                            <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#directives-links"' :
                                'data-target="#xs-directives-links"' }>
                                <span class="icon ion-md-code-working"></span>
                                <span>Directives</span>
                                <span class="icon ion-ios-arrow-down"></span>
                            </div>
                            <ul class="links collapse " ${ isNormalMode ? 'id="directives-links"' : 'id="xs-directives-links"' }>
                                <li class="link">
                                    <a href="directives/MenuSelectionDirective.html" data-type="entity-link">MenuSelectionDirective</a>
                                </li>
                                <li class="link">
                                    <a href="directives/MenuToggleDirective.html" data-type="entity-link">MenuToggleDirective</a>
                                </li>
                                <li class="link">
                                    <a href="directives/PasswordToggleDirective.html" data-type="entity-link">PasswordToggleDirective</a>
                                </li>
                                <li class="link">
                                    <a href="directives/RouterLinkDirectiveStub.html" data-type="entity-link">RouterLinkDirectiveStub</a>
                                </li>
                            </ul>
                        </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#classes-links"' :
                            'data-target="#xs-classes-links"' }>
                            <span class="icon ion-ios-paper"></span>
                            <span>Classes</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="classes-links"' : 'id="xs-classes-links"' }>
                            <li class="link">
                                <a href="classes/AccountIndex.html" data-type="entity-link">AccountIndex</a>
                            </li>
                            <li class="link">
                                <a href="classes/ActivatedRouteStub.html" data-type="entity-link">ActivatedRouteStub</a>
                            </li>
                            <li class="link">
                                <a href="classes/CustomErrorStateMatcher.html" data-type="entity-link">CustomErrorStateMatcher</a>
                            </li>
                            <li class="link">
                                <a href="classes/CustomValidator.html" data-type="entity-link">CustomValidator</a>
                            </li>
                            <li class="link">
                                <a href="classes/HttpError.html" data-type="entity-link">HttpError</a>
                            </li>
                            <li class="link">
                                <a href="classes/MutablePgpKeyStore.html" data-type="entity-link">MutablePgpKeyStore</a>
                            </li>
                            <li class="link">
                                <a href="classes/PGPSigner.html" data-type="entity-link">PGPSigner</a>
                            </li>
                            <li class="link">
                                <a href="classes/Settings.html" data-type="entity-link">Settings</a>
                            </li>
                            <li class="link">
                                <a href="classes/TokenRegistry.html" data-type="entity-link">TokenRegistry</a>
                            </li>
                            <li class="link">
                                <a href="classes/TokenServiceStub.html" data-type="entity-link">TokenServiceStub</a>
                            </li>
                            <li class="link">
                                <a href="classes/TransactionServiceStub.html" data-type="entity-link">TransactionServiceStub</a>
                            </li>
                            <li class="link">
                                <a href="classes/UserServiceStub.html" data-type="entity-link">UserServiceStub</a>
                            </li>
                        </ul>
                    </li>
                        <li class="chapter">
                            <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#injectables-links"' :
                                'data-target="#xs-injectables-links"' }>
                                <span class="icon ion-md-arrow-round-down"></span>
                                <span>Injectables</span>
                                <span class="icon ion-ios-arrow-down"></span>
                            </div>
                            <ul class="links collapse " ${ isNormalMode ? 'id="injectables-links"' : 'id="xs-injectables-links"' }>
                                <li class="link">
                                    <a href="injectables/AuthService.html" data-type="entity-link">AuthService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/BlockSyncService.html" data-type="entity-link">BlockSyncService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/ErrorDialogService.html" data-type="entity-link">ErrorDialogService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/GlobalErrorHandler.html" data-type="entity-link">GlobalErrorHandler</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/KeystoreService.html" data-type="entity-link">KeystoreService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/LocationService.html" data-type="entity-link">LocationService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/LoggingService.html" data-type="entity-link">LoggingService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/RegistryService.html" data-type="entity-link">RegistryService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/TokenService.html" data-type="entity-link">TokenService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/TransactionService.html" data-type="entity-link">TransactionService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/UserService.html" data-type="entity-link">UserService</a>
                                </li>
                                <li class="link">
                                    <a href="injectables/Web3Service.html" data-type="entity-link">Web3Service</a>
                                </li>
                            </ul>
                        </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#interceptors-links"' :
                            'data-target="#xs-interceptors-links"' }>
                            <span class="icon ion-ios-swap"></span>
                            <span>Interceptors</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="interceptors-links"' : 'id="xs-interceptors-links"' }>
                            <li class="link">
                                <a href="interceptors/ErrorInterceptor.html" data-type="entity-link">ErrorInterceptor</a>
                            </li>
                            <li class="link">
                                <a href="interceptors/HttpConfigInterceptor.html" data-type="entity-link">HttpConfigInterceptor</a>
                            </li>
                            <li class="link">
                                <a href="interceptors/LoggingInterceptor.html" data-type="entity-link">LoggingInterceptor</a>
                            </li>
                            <li class="link">
                                <a href="interceptors/MockBackendInterceptor.html" data-type="entity-link">MockBackendInterceptor</a>
                            </li>
                        </ul>
                    </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#guards-links"' :
                            'data-target="#xs-guards-links"' }>
                            <span class="icon ion-ios-lock"></span>
                            <span>Guards</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="guards-links"' : 'id="xs-guards-links"' }>
                            <li class="link">
                                <a href="guards/AuthGuard.html" data-type="entity-link">AuthGuard</a>
                            </li>
                            <li class="link">
                                <a href="guards/RoleGuard.html" data-type="entity-link">RoleGuard</a>
                            </li>
                        </ul>
                    </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#interfaces-links"' :
                            'data-target="#xs-interfaces-links"' }>
                            <span class="icon ion-md-information-circle-outline"></span>
                            <span>Interfaces</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? ' id="interfaces-links"' : 'id="xs-interfaces-links"' }>
                            <li class="link">
                                <a href="interfaces/AccountDetails.html" data-type="entity-link">AccountDetails</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Action.html" data-type="entity-link">Action</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Conversion.html" data-type="entity-link">Conversion</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Meta.html" data-type="entity-link">Meta</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/MetaResponse.html" data-type="entity-link">MetaResponse</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/MutableKeyStore.html" data-type="entity-link">MutableKeyStore</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Signable.html" data-type="entity-link">Signable</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Signature.html" data-type="entity-link">Signature</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Signature-1.html" data-type="entity-link">Signature</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Signer.html" data-type="entity-link">Signer</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Staff.html" data-type="entity-link">Staff</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Token.html" data-type="entity-link">Token</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Transaction.html" data-type="entity-link">Transaction</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/Tx.html" data-type="entity-link">Tx</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/TxToken.html" data-type="entity-link">TxToken</a>
                            </li>
                            <li class="link">
                                <a href="interfaces/W3.html" data-type="entity-link">W3</a>
                            </li>
                        </ul>
                    </li>
                        <li class="chapter">
                            <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#pipes-links"' :
                                'data-target="#xs-pipes-links"' }>
                                <span class="icon ion-md-add"></span>
                                <span>Pipes</span>
                                <span class="icon ion-ios-arrow-down"></span>
                            </div>
                            <ul class="links collapse " ${ isNormalMode ? 'id="pipes-links"' : 'id="xs-pipes-links"' }>
                                <li class="link">
                                    <a href="pipes/SafePipe.html" data-type="entity-link">SafePipe</a>
                                </li>
                                <li class="link">
                                    <a href="pipes/TokenRatioPipe.html" data-type="entity-link">TokenRatioPipe</a>
                                </li>
                            </ul>
                        </li>
                    <li class="chapter">
                        <div class="simple menu-toggler" data-toggle="collapse" ${ isNormalMode ? 'data-target="#miscellaneous-links"'
                            : 'data-target="#xs-miscellaneous-links"' }>
                            <span class="icon ion-ios-cube"></span>
                            <span>Miscellaneous</span>
                            <span class="icon ion-ios-arrow-down"></span>
                        </div>
                        <ul class="links collapse " ${ isNormalMode ? 'id="miscellaneous-links"' : 'id="xs-miscellaneous-links"' }>
                            <li class="link">
                                <a href="miscellaneous/functions.html" data-type="entity-link">Functions</a>
                            </li>
                            <li class="link">
                                <a href="miscellaneous/variables.html" data-type="entity-link">Variables</a>
                            </li>
                        </ul>
                    </li>
                        <li class="chapter">
                            <a data-type="chapter-link" href="routes.html"><span class="icon ion-ios-git-branch"></span>Routes</a>
                        </li>
                    <li class="chapter">
                        <a data-type="chapter-link" href="coverage.html"><span class="icon ion-ios-stats"></span>Documentation coverage</a>
                    </li>
                    <li class="divider"></li>
                    <li class="copyright">
                        Documentation generated using <a href="https://compodoc.app/" target="_blank">
                            <img data-src="images/compodoc-vectorise.png" class="img-responsive" data-type="compodoc-logo">
                        </a>
                    </li>
            </ul>
        </nav>
        `);
        this.innerHTML = tp.strings;
    }
});