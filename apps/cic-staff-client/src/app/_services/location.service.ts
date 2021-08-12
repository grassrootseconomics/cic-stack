import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '@src/environments/environment';
import { first } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root',
})
export class LocationService {
  areaNames: object = {};
  private areaNamesList: BehaviorSubject<object> = new BehaviorSubject<object>(this.areaNames);
  areaNamesSubject: Observable<object> = this.areaNamesList.asObservable();

  areaTypes: object = {};
  private areaTypesList: BehaviorSubject<object> = new BehaviorSubject<object>(this.areaTypes);
  areaTypesSubject: Observable<object> = this.areaTypesList.asObservable();

  constructor(private httpClient: HttpClient) {}

  getAreaNames(): void {
    this.httpClient
      .get(`${environment.cicMetaUrl}/areanames`)
      .pipe(first())
      .subscribe((res: object) => this.areaNamesList.next(res));
  }

  getAreaNameByLocation(location: string, areaNames: object): string {
    const keywords = location.toLowerCase().split(' ');
    for (const keyword of keywords) {
      const queriedAreaName: string = Object.keys(areaNames).find((key) =>
        areaNames[key].includes(keyword)
      );
      if (queriedAreaName) {
        return queriedAreaName;
      }
    }
    return 'other';
  }

  getAreaTypes(): void {
    this.httpClient
      .get(`${environment.cicMetaUrl}/areatypes`)
      .pipe(first())
      .subscribe((res: object) => this.areaTypesList.next(res));
  }

  getAreaTypeByArea(area: string, areaTypes: object): string {
    const keywords = area.toLowerCase().split(' ');
    for (const keyword of keywords) {
      const queriedAreaType: string = Object.keys(areaTypes).find((key) =>
        areaTypes[key].includes(keyword)
      );
      if (queriedAreaType) {
        return queriedAreaType;
      }
    }
    return 'other';
  }
}
