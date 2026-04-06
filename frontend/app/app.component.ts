import { Component } from '@angular/core';
import { ProposalComponent } from './pages/proposal/proposal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ProposalComponent],
  template: `<app-proposal></app-proposal>`
})
export class AppComponent {}
