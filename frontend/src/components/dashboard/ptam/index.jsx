// @module ptam/index — Re-exports do módulo PTAM (wizard + steps + shared)
export { default as PtamWizard } from './PtamWizard';
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
export { default as ProprietariosSection } from './shared/ProprietariosSection';
export { default as RuralDocSection, isRural } from './shared/RuralDocSection';
export * from './ptamHelpers';
