function getKairosContract() {
  return {
    enabled: false,
    activation_mode: 'explicit-opt-in',
    boundaries: {
      cannot_be_primary_brain: true,
      cannot_be_execution_authority: true,
      must_delegate_back_to_master: true,
    },
    scheduling_hooks: ['follow-up', 'scheduled-check', 'recurring-task'],
    context_policy: {
      memory_access: 'read-session-and-persistent-memory',
      transcript_access: 'read-latest-session-transcript',
      execution_policy: 'request-work-through-master-runtime',
    },
  };
}

module.exports = {
  getKairosContract,
};
