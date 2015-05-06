class SecurityQuestion(models.Model):
    security_question = models.CharField(max_length=255)
    is_other = models.BooleanField(default=False)  # indicates whether or not a particular question requires a text
                                                   # entry field for a question other than those listed.
    is_active = models.BooleanField(default=True)
    is_test_record = models.BooleanField(default=settings.TEST_RECORD_DEFAULT)

    class Meta:
        db_table = 'account_securityquestion'
        verbose_name = 'Security Question'
        verbose_name_plural = 'Security Questions'

    def __unicode__(self):
        return self.name

class SecurityQuestionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SecurityQuestionsForm, self).__init__(*args, **kwargs)

        if hasattr(settings, 'MAX_SECURITY_QUESTIONS'):
            question_count = settings.MAX_SECURITY_QUESTIONS
        else:
            question_count = 0

        self.questions = SecurityQuestion.objects.filter(is_active=True)
        # Generate question related field from db
        if len(self.questions):
            choices = [(q.id, q.security_question, int(q.is_other)) for q in self.questions]
            for question in range(0, question_count):
                choices_buf = [(-1, "Select a question #%d ..." % (question + 1), 0)] + choices
                question_key = 'question_%s' % question
                required = question_key in kwargs.get('initial')

                self.fields[question_key] = QuestionChoiceField(required=required,
                                                                label='Question %s' % (question + 1),
                                                                choices=choices_buf)
                self.fields['q_other_%s' % question] = forms.CharField(required=False,
                                                                       label='Custom Question')
                self.fields['answer_%s' % question] = forms.CharField(required=False,
                                                                      label='Answer')

    def extra_answers(self):
        for name, value in self.cleaned_data.items():
            if name.startswith('question_') and int(value) != -1:
                identifier = name.split('_')[-1]
                item = {
                    'security_question_id': value,
                    'security_question_other': self.cleaned_data['q_other_' + identifier],
                    'security_answer': self.cleaned_data['answer_' + identifier]
                }
                yield item

    def clean(self):
        super(SecurityQuestionsForm, self).clean()

        question_ids = []
        for name, value in self.cleaned_data.items():
            if name.startswith('question_') and int(value) != -1:
                question_ids.append((name.split('_')[-1], value))

        for question_id, value in question_ids:
            if not self.cleaned_data.get('answer_%s' % question_id):
                self.add_error('answer_%s' % question_id, 'This field is required.')
            question = self.questions.filter(id=value)[0]
            if question \
                    and question.is_other \
                    and not self.cleaned_data.get('q_other_%s' % question_id):
                self.add_error('q_other_%s' % question_id, 'This field is required.')

        if not len(question_ids):
            self.add_error('question_0', "Must submit at least one security answer.")

        return self.cleaned_data

class SecurityQuestionsView(FormView):
    template_name = 'account/security_questions.html'
    form_class = SecurityQuestionsForm
    success_url = '/account/questions/'

    def get_initial(self):
        answers = SecurityAnswer.objects.filter(owner=self.request.user)

        initial = {}
        count = 0
        for answer in answers:
            initial['question_%d' % count] = answer.security_question.id
            if answer.security_question_other:
                initial['q_other_%d' % count] = answer.security_question_other
            count += 1

        return initial

    def form_valid(self, form):
        user = self.request.user

        user.profile.set_answers(list(form.extra_answers()))
        return super(SecurityQuestionsView, self).form_valid(form)
