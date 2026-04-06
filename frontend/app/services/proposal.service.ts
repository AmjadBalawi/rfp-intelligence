import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ProposalService {
  private apiUrl = 'https://rfp-intelligence-2.onrender.com/api';

  generateProposal(rfpText: string): Observable<any> {
    return new Observable(observer => {
      fetch(`${this.apiUrl}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: rfpText })
      }).then(async response => {
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader!.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data) {
                try {
                  const parsed = JSON.parse(data);
                  observer.next(parsed);
                } catch (e) {
                  observer.next({ raw: data });
                }
              }
            }
          }
        }
        observer.complete();
      }).catch(err => observer.error(err));
    });
  }

  async seedCatalog() {
    const response = await fetch(`${this.apiUrl}/catalog/seed`, { method: 'POST' });
    return response.json();
  }
}
