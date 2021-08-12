import { Observable, of } from 'rxjs';

export class UserServiceStub {
  users = [
    {
      id: 1,
      name: 'John Doe',
      phone: '+25412345678',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'user',
      created: '08/16/2020',
      balance: '12987',
      failedPinAttempts: 1,
      status: 'approved',
      bio: 'Bodaboda',
      gender: 'male',
    },
    {
      id: 2,
      name: 'Jane Buck',
      phone: '+25412341234',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'vendor',
      created: '04/02/2020',
      balance: '56281',
      failedPinAttempts: 0,
      status: 'approved',
      bio: 'Groceries',
      gender: 'female',
    },
    {
      id: 3,
      name: 'Mc Donald',
      phone: '+25498765432',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'group',
      created: '11/16/2020',
      balance: '450',
      failedPinAttempts: 2,
      status: 'unapproved',
      bio: 'Food',
      gender: 'male',
    },
    {
      id: 4,
      name: 'Hera Cles',
      phone: '+25498769876',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'user',
      created: '05/28/2020',
      balance: '5621',
      failedPinAttempts: 3,
      status: 'approved',
      bio: 'Shop',
      gender: 'female',
    },
    {
      id: 5,
      name: 'Silver Fia',
      phone: '+25462518374',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'token agent',
      created: '10/10/2020',
      balance: '817',
      failedPinAttempts: 0,
      status: 'unapproved',
      bio: 'Electronics',
      gender: 'male',
    },
  ];

  actions = [
    { id: 1, user: 'Tom', role: 'enroller', action: 'Disburse RSV 100', approval: false },
    { id: 2, user: 'Christine', role: 'admin', action: 'Change user phone number', approval: true },
    { id: 3, user: 'Will', role: 'superadmin', action: 'Reclaim RSV 1000', approval: true },
    { id: 4, user: 'Vivian', role: 'enroller', action: 'Complete user profile', approval: true },
    { id: 5, user: 'Jack', role: 'enroller', action: 'Reclaim RSV 200', approval: false },
    {
      id: 6,
      user: 'Patience',
      role: 'enroller',
      action: 'Change user information',
      approval: false,
    },
  ];

  getUserById(id: string): any {
    return {
      id: 1,
      name: 'John Doe',
      phone: '+25412345678',
      address: '0xc86ff893ac40d3950b4d5f94a9b837258b0a9865',
      type: 'user',
      created: '08/16/2020',
      balance: '12987',
      failedPinAttempts: 1,
      status: 'approved',
      bio: 'Bodaboda',
      gender: 'male',
    };
  }

  getUser(userKey: string): Observable<any> {
    console.log('Here');
    return of({
      dateRegistered: 1595537208,
      key: {
        ethereum: [
          '0x51d3c8e2e421604e2b644117a362d589c5434739',
          '0x9D7c284907acbd4a0cE2dDD0AA69147A921a573D',
        ],
      },
      location: {
        external: {},
        latitude: '22.430670',
        longitude: '151.002995',
      },
      selling: ['environment', 'health', 'transport'],
      vcard:
        'QkVHSU46VkNBUkQNClZFUlNJT046My4wDQpFTUFJTDphYXJuZXNlbkBob3RtYWlsLmNvbQ0KRk46S3VydMKgS3JhbmpjDQpOOktyYW5qYztLdXJ0Ozs7DQpURUw7VFlQPUNFTEw6NjkyNTAzMzQ5ODE5Ng0KRU5EOlZDQVJEDQo=',
    });
  }

  getActionById(id: string): any {
    return {
      id: 1,
      user: 'Tom',
      role: 'enroller',
      action: 'Disburse RSV 100',
      approval: false,
    };
  }

  approveAction(id: number): any {
    return {
      id: 1,
      user: 'Tom',
      role: 'enroller',
      action: 'Disburse RSV 100',
      approval: true,
    };
  }
}
