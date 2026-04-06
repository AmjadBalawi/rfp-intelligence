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
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const reader = response.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const processChunk = (chunk: string) => {
            buffer += chunk;
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || '';

            for (const part of parts) {
              let jsonStr = part.trim();
              if (jsonStr.startsWith('data:')) {
                jsonStr = jsonStr.slice(5).trim(); // remove "data:"
              }
              if (jsonStr) {
                try {
                  const event = JSON.parse(jsonStr);
                  console.log('[SSE] Emitting:', event.node);
                  observer.next(event);
                } catch (e) {
                  console.warn('[SSE] Parse error:', jsonStr);
                }
              }
            }
          };

          const readStream = () => {
            reader.read().then(({ done, value }) => {
              const chunk = decoder.decode(value, { stream: !done });
              processChunk(chunk);

              if (done) {
                // Process any leftover buffer
                if (buffer.trim()) {
                  let leftover = buffer.trim();
                  if (leftover.startsWith('data:')) {
                    leftover = leftover.slice(5).trim();
                  }
                  try {
                    const event = JSON.parse(leftover);
                    observer.next(event);
                  } catch (e) {}
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
