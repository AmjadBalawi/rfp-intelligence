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
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const reader = response.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const readStream = () => {
            reader.read().then(({ done, value }) => {
              buffer += decoder.decode(value, { stream: !done });
              const parts = buffer.split('\n\n');
              buffer = parts.pop() || '';

              for (const part of parts) {
                if (part.startsWith('data: ')) {
                  const jsonStr = part.slice(6).trim();
                  if (jsonStr) {
                    try {
                      observer.next(JSON.parse(jsonStr));
                    } catch (e) {
                      console.warn('Failed to parse SSE data:', jsonStr);
                    }
                  }
                }
              }

              if (done) {
                if (buffer.startsWith('data: ')) {
                  const jsonStr = buffer.slice(6).trim();
                  if (jsonStr) {
                    try {
                      observer.next(JSON.parse(jsonStr));
                    } catch (e) {
                      console.warn('Failed to parse leftover SSE data:', jsonStr);
                    }
                  }
                }
                observer.complete();
                return;
              }
              readStream();
            }).catch(err => observer.error(err));
          };
          readStream();
        })
        .catch(err => observer.error(err));
    });
  }

  async seedCatalog() {
    const response = await fetch(`${this.apiUrl}/catalog/seed`, { method: 'POST' });
    return response.json();
  }
}
