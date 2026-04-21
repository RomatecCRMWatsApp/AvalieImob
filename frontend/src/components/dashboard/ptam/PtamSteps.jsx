// @module ptam/PtamSteps — Re-exports de compatibilidade (arquivo refatorado em steps/)
// Este arquivo existe apenas para manter compatibilidade com imports legados.
// Todos os componentes foram movidos para ./steps/ e ./shared/

export { StepSolicitante } from './steps/StepSolicitante';
export { StepObjetivo } from './steps/StepObjetivo';
export { StepImovelId } from './steps/StepImovelId';
export { StepRegiao } from './steps/StepRegiao';
export { StepCaracterizacao } from './steps/StepCaracterizacao';
export { StepAmostras } from './steps/StepAmostras';
export { StepMetodologia } from './steps/StepMetodologia';
export { StepCalculos } from './steps/StepCalculos';
export { StepPonderancia } from './steps/StepPonderancia';
export { StepMetodoAvaliacao } from './steps/StepMetodoAvaliacao';
export { StepResultado } from './steps/StepResultado';
export { StepConclusao } from './steps/StepConclusao';

// Legacy aliases
export { StepSolicitante as StepIdentification } from './steps/StepSolicitante';
export { StepImovelId as StepProperty } from './steps/StepImovelId';
export { StepRegiao as StepVistoria } from './steps/StepRegiao';
export { StepMetodologia as StepMethodology } from './steps/StepMetodologia';
export { StepAmostras as StepImpactAreas } from './steps/StepAmostras';
export { StepConclusao as StepConclusion } from './steps/StepConclusao';
