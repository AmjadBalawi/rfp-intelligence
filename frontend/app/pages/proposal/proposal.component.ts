import { Component } from '@angular/core';
import { ProposalService } from '../services/proposal.service';

@Component({
  selector: 'app-proposal',
  templateUrl: './proposal.component.html',
  styleUrls: ['./proposal.component.scss']
})
export class ProposalComponent {
  rfpText = '';
  loading = false;
  activeTab = 'pipeline';

  pipelineEvents: any[] = [];
  retrievedProducts: any[] = [];
  proposalBlocks: any[] = [];
  evaluation: any = null;

  constructor(private proposalService: ProposalService) {}

  onSubmit() {
    if (!this.rfpText.trim()) return;

    // Reset state
    this.pipelineEvents = [];
    this.retrievedProducts = [];
    this.proposalBlocks = [];
    this.evaluation = null;
    this.loading = true;
    this.activeTab = 'pipeline';  // show pipeline tab first

    this.proposalService.generateProposal(this.rfpText).subscribe({
      next: (event: any) => {
        // Handle different event types emitted by the service
        if (event.node && event.state !== undefined) {
          // Pipeline step event
          this.pipelineEvents.push(event);
        } else if (event.products) {
          // Retrieved products event
          this.retrievedProducts = event.products;
          this.activeTab = 'retrieval';  // auto switch to products
        } else if (event.blocks) {
          // Proposal blocks event
          this.proposalBlocks = event.blocks;
          this.activeTab = 'proposal';   // auto switch to proposal
        } else if (event.evaluation) {
          // Evaluation event
          this.evaluation = event.evaluation;
          this.activeTab = 'evaluation'; // auto switch to evaluation
        } else {
          // Fallback: if raw content arrives, accumulate or log
          console.log('Received:', event);
        }
      },
      error: (err) => {
        console.error('Generation error:', err);
        this.loading = false;
        // Optionally show an error message to the user
        alert('Failed to generate proposal. Check console or backend.');
      },
      complete: () => {
        this.loading = false;
      }
    });
  }

  seed() {
    this.proposalService.seedCatalog().then(res => {
      console.log('Catalog seeded:', res);
      alert('Catalog seeded successfully');
    }).catch(err => {
      console.error('Seed error:', err);
      alert('Failed to seed catalog');
    });
  }
}
