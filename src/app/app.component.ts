import { Component, ElementRef, ViewChild, signal, computed, effect, inject, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AiTutorService } from './services/ai-tutor.service';
import { ArtPlumComponent } from './components/art-plum.component';
import { Subscription } from 'rxjs';

interface ChatMessage {
  sender: 'user' | 'tutor';
  text: string;
  timestamp: Date;
  // true = answer passed the (simulated) math verifier; false = honest abstention;
  // undefined = system/welcome message, no badge shown
  verified?: boolean;
}

interface StudyTask {
  id: number;
  title: string;
  subject: string;
  completed: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, CommonModule, ArtPlumComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit, OnDestroy {
  private tutorService = inject(AiTutorService);
  private chatSubscription?: Subscription;

  @ViewChild('chatHistoryEl') private chatHistoryEl?: ElementRef<HTMLDivElement>;

  constructor() {
    // Keep the chat pinned to the latest message while replies stream in
    effect(() => {
      this.chatMessages();
      this.tutorIsTyping();
      setTimeout(() => {
        const el = this.chatHistoryEl?.nativeElement;
        if (el) el.scrollTop = el.scrollHeight;
      });
    });
  }

  // App title
  title = 'AITutor - Your Intelligent Study Companion';

  // Theme (class set before first paint by the index.html script)
  isDark = signal<boolean>(document.documentElement.classList.contains('dark'));

  // Signals
  selectedSubject = signal<string>('math');
  chatInput = signal<string>('');
  tutorIsTyping = signal<boolean>(false);
  
  chatMessages = signal<ChatMessage[]>([
    {
      sender: 'tutor',
      text: "Hello! I am your AI Study Companion. Select a subject category above (Math, Science, History, Coding) and ask me a question, or choose a quick prompt to see me in action!",
      timestamp: new Date()
    }
  ]);

  studyTasks = signal<StudyTask[]>([
    { id: 1, title: 'Understand limits & basic derivatives', subject: 'math', completed: true },
    { id: 2, title: 'Study Newton\'s laws vs Einstein\'s gravity', subject: 'science', completed: false },
    { id: 3, title: 'Summarize the milestones of the Space Race', subject: 'history', completed: false },
    { id: 4, title: 'Learn Angular 18 Signals reactivity', subject: 'coding', completed: true },
    { id: 5, title: 'Write an async/await script in TypeScript', subject: 'coding', completed: false }
  ]);

  // New task input state
  newTaskTitle = signal<string>('');

  // Computed properties (Signals)
  filteredTasks = computed(() => {
    return this.studyTasks().filter(task => task.subject === this.selectedSubject());
  });

  // Count within the selected subject so the progress bar matches the visible list
  completedTasksCount = computed(() => {
    return this.filteredTasks().filter(task => task.completed).length;
  });

  totalTasksCount = computed(() => {
    return this.filteredTasks().length;
  });

  completionProgressPercentage = computed(() => {
    const total = this.totalTasksCount();
    if (total === 0) return 0;
    return Math.round((this.completedTasksCount() / total) * 100);
  });

  // Pre-configured quick questions per subject
  quickPrompts = computed(() => {
    const sub = this.selectedSubject();
    if (sub === 'math') {
      return [
        'Explain the basic concepts of calculus.',
        'How do I solve the equation 2x + 5 = 15?'
      ];
    } else if (sub === 'science') {
      return [
        'Explain General Relativity and gravity.',
        'What is superposition in quantum physics?'
      ];
    } else if (sub === 'history') {
      return [
        'What happened during the Space Race?',
        'Tell me about ancient civilizations.'
      ];
    } else if (sub === 'coding') {
      return [
        'What is new in Angular 18?',
        'How do JavaScript Promises work?'
      ];
    }
    return [];
  });

  ngOnInit() {}

  ngOnDestroy() {
    this.chatSubscription?.unsubscribe();
  }

  toggleTheme() {
    const dark = !this.isDark();
    this.isDark.set(dark);
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }

  selectSubject(subject: string) {
    this.selectedSubject.set(subject);
  }

  sendMessage() {
    const promptText = this.chatInput().trim();
    if (!promptText) return;

    this.executeChat(promptText);
    this.chatInput.set('');
  }

  askQuickPrompt(promptText: string) {
    this.executeChat(promptText);
  }

  private executeChat(promptText: string) {
    // Cancel any previous stream
    if (this.chatSubscription) {
      this.chatSubscription.unsubscribe();
    }

    // Add User Message
    this.chatMessages.update(msgs => [
      ...msgs,
      {
        sender: 'user',
        text: promptText,
        timestamp: new Date()
      }
    ]);

    // Show tutor typing state
    this.tutorIsTyping.set(true);

    // Prepare container for tutor's streamed response
    let tutorMessageIndex = -1;

    const ensureTutorMessage = () => {
      if (tutorMessageIndex !== -1) return;
      this.tutorIsTyping.set(false);
      tutorMessageIndex = this.chatMessages().length;
      this.chatMessages.update(msgs => [
        ...msgs,
        { sender: 'tutor', text: '', timestamp: new Date() }
      ]);
    };

    const patchTutorMessage = (patch: Partial<ChatMessage>) => {
      if (tutorMessageIndex === -1) return;
      this.chatMessages.update(msgs => {
        const updated = [...msgs];
        updated[tutorMessageIndex] = { ...updated[tutorMessageIndex], ...patch };
        return updated;
      });
    };

    // Stream the answer from the backend; the verification verdict arrives
    // as its own event once the full answer has streamed in
    this.chatSubscription = this.tutorService
      .streamResponse(this.selectedSubject(), promptText)
      .subscribe({
        next: (event) => {
          switch (event.type) {
            case 'token':
              ensureTutorMessage();
              this.chatMessages.update(msgs => {
                const updated = [...msgs];
                updated[tutorMessageIndex] = {
                  ...updated[tutorMessageIndex],
                  text: updated[tutorMessageIndex].text + event.text
                };
                return updated;
              });
              break;
            case 'verification':
              patchTutorMessage({ verified: event.verified ?? false });
              break;
            case 'error':
              ensureTutorMessage();
              patchTutorMessage({
                text: 'Something went wrong while reaching the tutor service. Please try again.',
                verified: false
              });
              break;
          }
        },
        error: (err) => {
          console.error(err);
          this.tutorIsTyping.set(false);
          ensureTutorMessage();
          patchTutorMessage({
            text: 'The tutor service is unreachable right now. Make sure the backend is running, then try again.',
            verified: false
          });
        },
        complete: () => {
          this.tutorIsTyping.set(false);
        }
      });
  }

  // Study Planner Methods
  addTask() {
    const title = this.newTaskTitle().trim();
    if (!title) return;

    const newId = this.studyTasks().length > 0 
      ? Math.max(...this.studyTasks().map(t => t.id)) + 1 
      : 1;

    const newTask: StudyTask = {
      id: newId,
      title: title,
      subject: this.selectedSubject(),
      completed: false
    };

    this.studyTasks.update(tasks => [...tasks, newTask]);
    this.newTaskTitle.set('');
  }

  toggleTask(taskId: number) {
    this.studyTasks.update(tasks => 
      tasks.map(t => t.id === taskId ? { ...t, completed: !t.completed } : t)
    );
  }

  deleteTask(taskId: number) {
    this.studyTasks.update(tasks => tasks.filter(t => t.id !== taskId));
  }

  clearChat() {
    if (this.chatSubscription) {
      this.chatSubscription.unsubscribe();
    }
    this.tutorIsTyping.set(false);
    this.chatMessages.set([
      {
        sender: 'tutor',
        text: `Chat reset. I'm ready for new questions on ${this.selectedSubject().toUpperCase()}!`,
        timestamp: new Date()
      }
    ]);
  }
}
