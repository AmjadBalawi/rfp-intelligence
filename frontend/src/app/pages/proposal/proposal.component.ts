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
  pipelineEvents: any[] = [];
  retrievedProducts: any[] = [];
  proposalBlocks: any[] = [];
  evaluation: any = null;
  activeTab = 'pipeline';
  loading = false;

  constructor(private service: ProposalService) {}

  onSubmit() {
    this.loading = true;
    this.pipelineEvents = [];
    this.retrievedProducts = [];
    this.proposalBlocks = [];
    this.evaluation = null;

    this.service.generateProposal(this.rfpText).subscribe({
      next: (data) => {
        this.pipelineEvents.push(data);
        if (data.node === 'retrieve') this.retrievedProducts = data.state.retrieved_products;
        if (data.node === 'generate') this.proposalBlocks = data.state.generated_blocks;
        if (data.node === 'evaluate') this.evaluation = data.state.evaluation;
      },
      complete: () => this.loading = false,
      error: (err) => { console.error(err); this.loading = false; }
    });
  }

  seed() {
    this.service.seedCatalog().then(() => alert('Catalog seeded'));
  }
}
