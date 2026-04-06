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
              // Decode and accumulate
              buffer += decoder.decode(value, { stream: !done });

              // Split by double newline (SSE standard)
              let parts = buffer.split('\n\n');
              buffer = parts.pop() || '';

              for (const part of parts) {
                if (part.startsWith('data: ')) {
                  const jsonStr = part.slice(6).trim();
                  if (jsonStr) {
                    try {
                      const event = JSON.parse(jsonStr);
                      console.log('[SSE] Received:', event.node, event.state); // Debug
                      observer.next(event);
                    } catch (e) {
                      console.warn('[SSE] Parse error:', jsonStr);
                    }
                  }
                } else if (part.trim()) {
                  // Some backends send without 'data:' prefix – try parsing anyway
                  try {
                    const event = JSON.parse(part);
                    console.log('[SSE] Raw JSON:', event);
                    observer.next(event);
                  } catch (e) {
                    console.warn('[SSE] Unknown format:', part);
                  }
                }
              }

              if (done) {
                // Process any leftover data
                if (buffer.startsWith('data: ')) {
                  const jsonStr = buffer.slice(6).trim();
                  if (jsonStr) {
                    try {
                      observer.next(JSON.parse(jsonStr));
                    } catch (e) {}
                  }
                } else if (buffer.trim()) {
                  try {
                    observer.next(JSON.parse(buffer));
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
