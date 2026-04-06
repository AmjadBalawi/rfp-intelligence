import { Component, ChangeDetectorRef } from '@angular/core';
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

  constructor(
    private proposalService: ProposalService,
    private cdr: ChangeDetectorRef
  ) {}

 onSubmit() {
  if (!this.rfpText.trim() || this.loading) return;

  this.pipelineEvents = [];
  this.retrievedProducts = [];
  this.proposalBlocks = [];
  this.evaluation = null;
  this.loading = true;
  this.activeTab = 'pipeline';
  this.cdr.detectChanges();

  const timeout = setTimeout(() => {
    if (this.loading) {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }, 60000);

  this.proposalService.generateProposal(this.rfpText).subscribe({
    next: (event: any) => {
      console.log('Event:', event);
      if (event?.node && event.state) {
        this.pipelineEvents.push({ node: event.node, state: event.state });

        // Try multiple possible property names
        const state = event.state;
        switch (event.node) {
          case 'retrieve':
            const products = state.retrieved_products || state.products;
            if (products) {
              this.retrievedProducts = [...products];
              this.activeTab = 'retrieval';
              this.cdr.detectChanges();
            }
            break;
          case 'generate':
            const blocks = state.generated_blocks || state.blocks || state.proposal_blocks;
            if (blocks && Array.isArray(blocks)) {
              this.proposalBlocks = [...blocks];
              this.activeTab = 'proposal';
              console.log('Proposal blocks count:', this.proposalBlocks.length);
              this.cdr.detectChanges();
            } else {
              console.warn('No blocks found in state:', state);
            }
            break;
          case 'evaluate':
            const evalData = state.evaluation || state.scores;
            if (evalData) {
              this.evaluation = evalData;
              this.activeTab = 'evaluation';
              this.loading = false;
              clearTimeout(timeout);
              this.cdr.detectChanges();
              alert('✅ Proposal generated!');
            } else {
              console.warn('No evaluation found in state:', state);
            }
            break;
          default:
            console.log(`Pipeline node: ${event.node}`);
        }
      } else {
        console.warn('Event missing node or state:', event);
      }
    },
    error: (err) => {
      console.error(err);
      this.loading = false;
      alert('Generation failed');
    },
    complete: () => {
      if (this.loading) {
        this.loading = false;
        clearTimeout(timeout);
        this.cdr.detectChanges();
      }
    }
  });
}
  seed() {
    this.proposalService.seedCatalog()
      .then(res => {
        console.log('Catalog seeded:', res);
        alert('Catalog seeded successfully');
      })
      .catch(err => {
        console.error('Seed error:', err);
        alert('Failed to seed catalog');
      });
  }
}
