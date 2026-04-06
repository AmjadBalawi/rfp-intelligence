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
  if (!this.rfpText.trim()) return;

  // Reset state
  this.pipelineEvents = [];
  this.retrievedProducts = [];
  this.proposalBlocks = [];
  this.evaluation = null;
  this.loading = true;
  this.activeTab = 'pipeline';

  this.proposalService.generateProposal(this.rfpText).subscribe({
    next: (event: any) => {
      // Every SSE message has a node and state
      if (event.node && event.state !== undefined) {
        // Log pipeline step
        this.pipelineEvents.push(event);

        // Extract actual data based on node type
        if (event.node === 'retrieve' && event.state.retrieved_products) {
          this.retrievedProducts = event.state.retrieved_products;
          this.activeTab = 'retrieval';
        } else if (event.node === 'generate' && event.state.generated_blocks) {
          this.proposalBlocks = event.state.generated_blocks;
          this.activeTab = 'proposal';
        } else if (event.node === 'evaluate' && event.state.evaluation) {
          this.evaluation = event.state.evaluation;
          this.activeTab = 'evaluation';
        }
      } else {
        // Fallback for any other unexpected shape
        console.log('Received unexpected event:', event);
      }
    },
    error: (err) => {
      console.error('Generation error:', err);
      this.loading = false;
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
