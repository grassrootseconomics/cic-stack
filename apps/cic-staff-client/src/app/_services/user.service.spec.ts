import { TestBed } from '@angular/core/testing';

import { UserService } from '@app/_services/user.service';
import { HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

describe('UserService', () => {
  let httpClient: HttpClient;
  let httpTestingController: HttpTestingController;
  let service: UserService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    httpClient = TestBed.inject(HttpClient);
    httpTestingController = TestBed.inject(HttpTestingController);
    service = TestBed.inject(UserService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return action for available id', () => {
    expect(service.getActionById('1')).toEqual({
      id: 1,
      user: 'Tom',
      role: 'enroller',
      action: 'Disburse RSV 100',
      approval: false,
    });
  });

  it('should not return action for unavailable id', () => {
    expect(service.getActionById('9999999999')).toBeUndefined();
  });

  it('should switch action approval from false to true', () => {
    service.approveAction('1');
    expect(service.getActionById('1')).toEqual({
      id: 1,
      user: 'Tom',
      role: 'enroller',
      action: 'Disburse RSV 100',
      approval: true,
    });
  });

  it('should switch action approval from true to false', () => {
    service.revokeAction('2');
    expect(service.getActionById('2')).toEqual({
      id: 2,
      user: 'Christine',
      role: 'admin',
      action: 'Change user phone number',
      approval: false,
    });
  });
});
