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
    if (this.loading) {
      this.loading = false;
      console.warn('Loading stopped by timeout');
    }
  }, 60000);

  this.proposalService.generateProposal(this.rfpText).subscribe({
    next: (event: any) => {
      console.log('Event:', event); // Debug

      if (event.node && event.state !== undefined) {
        this.pipelineEvents.push(event);

        // Handle retrieve
        if (event.node === 'retrieve' && event.state.retrieved_products) {
          this.retrievedProducts = [...event.state.retrieved_products];
          this.activeTab = 'retrieval';
        }
        // Handle generate (proposal blocks)
        else if (event.node === 'generate' && event.state.generated_blocks) {
          this.proposalBlocks = [...event.state.generated_blocks];
          this.activeTab = 'proposal';
          console.log('Proposal blocks set:', this.proposalBlocks.length);
        }
        // Handle evaluate
        else if (event.node === 'evaluate' && event.state.evaluation) {
          this.evaluation = event.state.evaluation;
          this.activeTab = 'evaluation';
          this.loading = false;
          clearTimeout(timeout);
          alert('✅ Proposal generated successfully!');
        }
      }
    },
    error: (err) => {
      console.error('Generation error:', err);
      this.loading = false;
      clearTimeout(timeout);
      alert('Failed to generate proposal.');
    },
    complete: () => {
      if (this.loading) {
        this.loading = false;
        clearTimeout(timeout);
      }
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
