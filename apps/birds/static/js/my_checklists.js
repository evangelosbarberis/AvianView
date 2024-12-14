const { createApp } = Vue;

createApp({
  data() {
    return {
      checklists: [],
      searchQuery: '',
    };
  },
  computed: {
    filteredChecklists() {
      return this.checklists.filter(checklist => 
        checklist.COMMON_NAME.toLowerCase().includes(this.searchQuery.toLowerCase())
      );
    }
  },
  methods: {
    async fetchChecklists() {
      try {
        const response = await axios.get('/birds/get_my_checklists');
        this.checklists = response.data.checklists;
      } catch (error) {
        console.error('Error fetching checklists:', error);
      }
    },
    async deleteChecklist(id) {
      try {
        const response = await axios.delete(`/birds/delete_checklist/${id}`);
        if (response.data.status === 'success') {
          this.checklists = this.checklists.filter(checklist => checklist.id !== id);
        }
      } catch (error) {
        console.error('Error deleting checklist:', error);
      }
    },
    addNewChecklist() {
      window.location.href = '/birds/add_checklist';
    },
    editChecklist(index) {
      const checklistId = this.checklists[index].id;
      window.location.href = `/birds/edit_checklist/${checklistId}`;
    }
  },
  mounted() {
    this.fetchChecklists();
  }
}).mount('#app');