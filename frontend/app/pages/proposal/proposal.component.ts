import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProposalService } from '../../services/proposal.service';

@Component({
  selector: 'app-proposal',
  standalone: true,
  imports: [CommonModule, FormsModule],
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
  if (!this.rfpText.trim() || this.loading) return;

  this.pipelineEvents = [];
  this.retrievedProducts = [];
  this.proposalBlocks = [];
  this.evaluation = null;
  this.loading = true;
  this.activeTab = 'pipeline';

  const timeout = setTimeout(() => {
    if (this.loading) this.loading = false;
  }, 60000);

  this.proposalService.generateProposal(this.rfpText).subscribe({
    next: (event: any) => {
      console.log('Raw event:', event);
      if (event?.node && event.state) {
        this.pipelineEvents.push({ node: event.node, state: event.state });
        switch (event.node) {
          case 'retrieve':
            if (event.state.retrieved_products) {
              this.retrievedProducts = [...event.state.retrieved_products];
              this.activeTab = 'retrieval';
            }
            break;
          case 'generate':
            if (event.state.generated_blocks) {
              this.proposalBlocks = [...event.state.generated_blocks];
              this.activeTab = 'proposal';
              console.log('Proposal blocks set:', this.proposalBlocks);
            }
            break;
          case 'evaluate':
            if (event.state.evaluation) {
              this.evaluation = event.state.evaluation;
              this.activeTab = 'evaluation';
              this.loading = false;
              clearTimeout(timeout);
              alert('✅ Proposal generated!');
            }
            break;
          default:
            console.log('Pipeline node:', event.node);
        }
      }
    },
    error: (err) => {
      console.error(err);
      this.loading = false;
      alert('Generation failed');
    },
    complete: () => {
      console.log('Stream complete');
      if (this.loading) this.loading = false;
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
