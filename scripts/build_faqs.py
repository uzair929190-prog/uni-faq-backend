# ===== build_faqs.py : faqs.csv aur test_cases.csv automatically banata hai =====
# Har entry = (category, answer, [sawal/paraphrases], [test sawal])
# Test sawal FAQ mein nahi hote, naye alfaaz mein hote hain (accuracy naapne ke liye)
# ZAROORI: neeche ke numbers/policies SAMPLE hain. Apni uni ke asli data se replace karo,
# phir  python scripts/build_faqs.py  dobara chalao.
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent   # backend/ folder

DATA = [
    # ---------- Pehli 5 entries (ids 1-13) ----------
    ("Admissions", "Admissions close on 15th August through the online portal.",
     ["What is the last date to apply?", "admission ki last date kya hai", "when does admission close"],
     ["admission kab tak open hai"]),
    ("Fee Structure", "BSCS semester fee is PKR 85000 in two installments.",
     ["What is the BSCS semester fee?", "bscs ki fee kitni hai", "how much is the fee for computer science"],
     ["fees kitni lagti hai cs ki"]),
    ("Hostel", "Yes separate hostels for boys and girls are available.",
     ["Is hostel available?", "hostel ki facility hai kya", "do you provide accommodation for students"],
     ["kya hostel mil sakta hai"]),
    ("Scholarships", "Students with 85 percent marks get merit scholarships. Need based forms are on the portal.",
     ["How can I get a scholarship?", "scholarship kaise milti hai"],
     ["scholarship milti hai kya"]),
    ("Exams", "75 percent attendance is required to sit in the final exams.",
     ["What is the minimum attendance for exams?", "exam mein baithne ke liye attendance kitni chahiye"],
     ["kitni attendance zaroori hai"]),

    # ---------- FEE STRUCTURE ----------
    ("Fee Structure", "The first semester fee is PKR 105000. It includes admission fee, security deposit and registration charges, so it is higher than later semesters.",
     ["What is the first semester fee?", "pehle semester ki fee kitni hoti hai", "first semester mein total kitne paise lagte hain", "fee structure of 1st semester"],
     ["pehle semester mein kitni fees deni hoti hai"]),
    ("Fee Structure", "Semester fee by program: BSCS PKR 85000, BSAI PKR 90000, BSSE PKR 85000, BBA PKR 70000, BS Electrical Engineering PKR 95000.",
     ["What is the fee of different degree programs?", "kis degree ki fee kitni hai", "BSAI ki fee kitni hai", "BBA fee structure"],
     ["artificial intelligence degree ki semester fees"]),
    ("Fee Structure", "Fee can be paid in 2 installments. The second installment is due within 45 days of semester start. Apply to the accounts office before the due date.",
     ["Can I pay my fee in installments?", "fee qiston mein de sakte hain", "installment ka option hai kya"],
     ["kya fees ek saath dena zaroori hai"]),
    ("Fee Structure", "A late fee of PKR 500 per day is charged after the due date. The maximum late fee is PKR 5000.",
     ["What is the late fee fine?", "fee late jama karwane pe jurmana kitna hai", "due date ke baad fee jama ho to kya hoga"],
     ["fee ki date nikal jaye to kitna fine lagta hai"]),
    ("Fee Structure", "Admission fee is refundable only before the semester starts. The security deposit is refunded after degree completion.",
     ["Is the fee refundable?", "fee wapis milti hai kya", "admission cancel karne pe refund milega"],
     ["agar main admission cancel kar doon to paise wapis milenge"]),
    ("Fee Structure", "Fee can be paid by bank challan, online banking or at the university accounts office. The challan is downloaded from the student portal.",
     ["How do I pay the fee?", "fee kahan aur kaise jama karwani hai", "fee challan kahan se milega"],
     ["challan kahan se download karna hai"]),
    ("Fee Structure", "MS Computer Science fee is PKR 60000 per semester. MBA fee is PKR 75000 per semester.",
     ["What is the MS fee?", "MS ki fee kitni hai", "MBA ki fee kitni hai"],
     ["master level par fees ka kharcha"]),
    ("Fee Structure", "A second sibling at the university gets a 10 percent tuition discount. Children of staff get a 20 percent discount.",
     ["Is there a sibling discount?", "bhai behan ko fee mein discount milta hai", "staff ke bachon ki fee kitni hai"],
     ["do bhai ek hi uni mein hon to concession"]),

    # ---------- FIRST SEMESTER ----------
    ("First Semester", "Bring original matric and inter certificates, CNIC or B-Form copy, 4 passport photos, domicile copy and the fee payment receipt on the joining day.",
     ["What should I bring on the first day?", "pehle din kya documents lane hain", "joining ke waqt kya chahiye"],
     ["university join karte waqt kaunse kagzat saath laun"]),
    ("First Semester", "Orientation week is held before classes start. It covers a campus tour, department introduction, portal registration and university rules. Attendance is mandatory.",
     ["What is orientation week?", "orientation kab hota hai", "pehle hafte mein kya hota hai"],
     ["classes se pehle koi introduction session hota hai"]),
    ("First Semester", "A typical first semester has 5 to 6 courses and 15 to 17 credit hours.",
     ["How many courses are in the first semester?", "pehle semester mein kitne subjects hote hain", "first semester credit hours"],
     ["first semester mein kitni courses parhni hoti hain"]),
    ("First Semester", "After admission you receive student portal login details by email. Use the portal to register courses, check attendance and download the fee challan.",
     ["How do I register for courses?", "student portal kaise use karte hain", "course registration kaise karte hain"],
     ["portal ka login kaise milega"]),

    # ---------- CGPA AND GRADING ----------
    ("CGPA and Grading", "Grading uses a 4.0 scale. A is 4.0, A- is 3.67, B+ is 3.33, B is 3.0, B- is 2.67, C+ is 2.33, C is 2.0, D is 1.0 and F is 0 which means fail.",
     ["What is the grading system?", "grading scale kya hai", "A grade ke kitne points hote hain", "marks se grade kaise banta hai"],
     ["grade points ka system kya hai"]),
    ("CGPA and Grading", "GPA is the average of one semester. CGPA is the average of all semesters weighted by credit hours. CGPA equals total quality points divided by total credit hours.",
     ["How is CGPA calculated?", "CGPA kaise nikalte hain", "GPA aur CGPA mein kya farq hai"],
     ["cgpa ka formula kya hai"]),
    ("CGPA and Grading", "The minimum CGPA to stay enrolled and to get the degree is 2.0. Below 2.0 the student is placed on academic probation.",
     ["What is the minimum CGPA required?", "kam az kam CGPA kitni honi chahiye", "CGPA 2 se kam ho to kya hoga", "academic probation kya hai"],
     ["degree ke liye minimum cgpa kitni chahiye"]),
    ("CGPA and Grading", "A failed or low grade course can be repeated. The new grade replaces the old one in the CGPA. Apply for repeat at the start of the semester.",
     ["How can I improve my CGPA?", "CGPA behtar kaise karein", "fail subject dobara kaise parhte hain", "course repeat policy"],
     ["agar koi paper fail ho jaye to kya karna hoga"]),
    ("CGPA and Grading", "Students with a semester GPA of 3.5 or above are placed on the Dean's honor list. A gold medal is awarded to the top CGPA student of each batch.",
     ["What is the Dean's honor list?", "honor list ke liye kitni GPA chahiye", "gold medal kab milta hai"],
     ["top student ko kya award milta hai"]),
    ("CGPA and Grading", "To keep a merit scholarship you need a CGPA of 3.5 or above in every semester.",
     ["How do I retain my scholarship?", "scholarship barqarar rakhne ke liye CGPA kitni chahiye"],
     ["scholarship jaari rakhne ki shart kya hai"]),

    # ---------- EXAMS ----------
    ("Exams", "Final exams start in the second week of December for fall and in June for spring. The datesheet is posted on the student portal.",
     ["When will the final exams start?", "final exams kab hon ge", "datesheet kab aati hai"],
     ["paper kab shuru honge"]),
    ("Exams", "Marks for theory courses are distributed as quizzes and assignments 20 percent, midterm 30 percent and final exam 50 percent.",
     ["How are marks distributed?", "midterm aur final ke kitne marks hote hain", "marks distribution kya hai"],
     ["quiz assignment aur paper ke marks ka breakdown"]),
    ("Exams", "Results are announced on the student portal within 2 weeks after the exams end.",
     ["When will the result be announced?", "result kab aata hai", "result kahan dekhna hai"],
     ["paper ka nateeja kitne din mein aata hai"]),
    ("Exams", "Paper rechecking can be requested within 7 days of the result by paying PKR 1000 per course at the exam office.",
     ["How can I get my paper rechecked?", "paper recheck kaise karwate hain", "marks se satisfied nahi to kya karein"],
     ["number kam aaye to dobara check karwana hai"]),
    ("Exams", "Cheating or any unfair means in an exam results in an F grade in that course and disciplinary action. Repeated cases can lead to expulsion.",
     ["What is the cheating policy?", "nakal karne pe kya saza hai", "unfair means ki punishment kya hai"],
     ["paper mein nakal pakri jaye to kya hoga"]),
    ("Exams", "A missed midterm or final can be retaken only for a valid reason such as illness with a medical certificate. Apply to the exam office within 3 days.",
     ["What if I miss an exam?", "paper miss ho jaye to kya karein", "bimari ki wajah se exam na de sakoon"],
     ["agar exam wale din bimar ho jaun"]),

    # ---------- ADMISSIONS ----------
    ("Admissions", "BS programs need at least 50 percent marks in intermediate or equivalent. BSCS and BSAI need Mathematics in intermediate (FSc Pre-Engineering or ICS). Admission is on merit.",
     ["What is the eligibility for BS admission?", "admission ke liye kitne marks chahiye", "BSCS ke liye FA wale apply kar sakte hain", "kya main ICS ke baghair apply kar sakta hoon"],
     ["bscs mein dakhle ke liye kya qualification chahiye"]),
    ("Admissions", "The entry test is 100 marks: Mathematics 40, English 30, Analytical and IQ 30. The passing mark is 50. The test is held in July at the campus.",
     ["How is the entry test?", "entry test mein kya aata hai", "entry test ka pattern kya hai"],
     ["test mein kin cheezon se sawal aate hain"]),
    ("Admissions", "Merit is calculated as 10 percent matric, 40 percent intermediate and 50 percent entry test.",
     ["How is merit calculated?", "merit formula kya hai", "merit list kaise banti hai"],
     ["merit banane ka tareeqa batayen"]),
    ("Admissions", "Documents required: matric and intermediate certificates, CNIC or B-Form, 4 passport photos, domicile and the entry test result.",
     ["What documents are required for admission?", "admission form ke saath kaunse documents lagte hain"],
     ["admission ke liye kon se kaghzat chahiye"]),
    ("Admissions", "Apply online on the university portal: create an account, fill the form, upload documents, pay the PKR 2000 form fee and print the roll number slip.",
     ["How do I apply for admission?", "admission form kaise bharte hain", "online apply karne ka process"],
     ["apply karne ke steps kya hain"]),
    ("Admissions", "Transfer from another university is allowed in the first 3 semesters. Credit hours are evaluated by the department committee.",
     ["Can I transfer from another university?", "kisi aur university se transfer ho sakta hai"],
     ["dusri uni se yahan aana chahta hoon"]),
    ("Admissions", "Reserved seats exist for disabled students, minorities and sports achievers. Submit the supporting certificates with the admission form.",
     ["Are there reserved seats?", "quota seats hain", "sports quota admission"],
     ["khilariyon ke liye khaas nashistein"]),
    ("Admissions", "MS admission needs 16 years of education with a CGPA of at least 2.5. There is an admission test and an interview. Fall admissions open in July.",
     ["How can I apply for MS?", "MS mein admission kaise lein", "master degree ki eligibility kya hai"],
     ["ms karne ke liye kya shartein hain"]),
    ("Admissions", "International students apply through the international office with a passport copy, academic transcripts and English proficiency. Hostel is available.",
     ["Can foreign students apply?", "international students admission", "overseas Pakistani students admission"],
     ["bahar ke mulk ke talba ke liye dakhla"]),
    ("Admissions", "Convocation is held once a year in March for the graduates of the previous year. Invitations and gown details are sent by email.",
     ["When is convocation?", "convocation kab hota hai", "degree distribution ceremony kab hai"],
     ["graduation ceremony kis mahine mein hoti hai"]),

    # ---------- DEGREE PROGRAMS ----------
    ("Degree Programs", "There is no single best degree. BSCS suits general software and IT jobs. BSSE focuses on building large software systems. BSAI focuses on machine learning and data. BBA suits management careers. Choose by your interest and Math strength.",
     ["Which degree is better?", "kaun si degree behtar hai", "BSCS ya BSAI mein se kaun si lun", "mujhe konsi degree leni chahiye", "which program has the best scope"],
     ["kis field mein admission lena chahiye"]),
    ("Degree Programs", "Undergraduate programs: BS Computer Science, BS Artificial Intelligence, BS Software Engineering, BS Data Science, BBA and BS Electrical Engineering. Master programs: MS Computer Science and MBA.",
     ["What degrees does the university offer?", "university mein kaun kaun si degrees hain", "programs ki list batao"],
     ["yahan kon kon se programs parhaye jate hain"]),
    ("Degree Programs", "BS programs take 4 years (8 semesters). Master programs take 2 years (4 semesters).",
     ["How long is the BS degree?", "BS kitne saal ka hota hai", "degree ki duration kya hai"],
     ["graduation mein kitna time lagta hai"]),
    ("Degree Programs", "BSCS covers broad computing: programming, databases, networks and software. BSAI shares the first two semesters and then adds machine learning, deep learning, NLP and computer vision.",
     ["What is the difference between BSCS and BSAI?", "BSCS aur BSAI mein kya farq hai"],
     ["cs aur ai ki degree mein kya fark hai"]),
    ("Degree Programs", "Computer Science and AI graduates work as software engineers, data scientists, ML engineers and freelancers. The career office organizes a job fair every year.",
     ["What is the scope after BSCS?", "BSCS ke baad jobs kya hain", "career scope kya hai"],
     ["degree ke baad naukri ke mauqe"]),
    ("Degree Programs", "A BS degree needs about 130 credit hours across 8 semesters.",
     ["How many credit hours are needed for BS?", "degree ke total credit hours kitne hain"],
     ["bs complete karne ke liye kitne credit hours"]),

    # ---------- DEPARTMENTS ----------
    ("Departments", "Departments: Computer Science, Artificial Intelligence, Software Engineering, Electrical Engineering, Business Administration and Mathematics and Sciences.",
     ["What departments does the university have?", "university ke departments kaun se hain", "department list batao"],
     ["yahan kitne shobe hain"]),
    ("Departments", "The CS and AI departments are in Block A. Business is in Block B and Engineering is in Block C.",
     ["Where is the CS department?", "CS department kahan hai", "blocks ki location kya hai"],
     ["computer science ka block kaunsa hai"]),

    # ---------- CONTACT ----------
    ("Contact", "Contact the admission office at admissions@university.edu.pk or call 041-0000000. Office hours are 9 AM to 4 PM, Monday to Friday.",
     ["How can I contact the university?", "university ka phone number kya hai", "admission office se rabta kaise karein"],
     ["office ka email kya hai"]),

    # ---------- TIME TABLE ----------
    ("Time Table", "Classes run Monday to Friday from 8:30 AM to 4:30 PM. Saturday and Sunday are off. Each lecture is 90 minutes.",
     ["What are the class timings?", "classes kitne baje start hoti hain", "university timings kya hain", "kya Saturday ko classes hoti hain"],
     ["kitne baje se kitne baje tak class hoti hai"]),
    ("Time Table", "The class timetable is published on the student portal and the department notice board a week before classes start.",
     ["Where can I see my timetable?", "time table kahan se milega", "timetable kab milta hai"],
     ["class schedule kahan dekhun"]),
    ("Time Table", "Lunch and prayer break is from 1:00 PM to 2:00 PM.",
     ["What is the break time?", "break kitne baje hoti hai", "namaz ka break kab hota hai"],
     ["lunch break kab hoti hai"]),
    ("Time Table", "The fall semester runs from September to January and the spring semester from February to June. Each semester has 16 teaching weeks plus exams.",
     ["When does the semester start?", "semester kab shuru hota hai", "academic calendar kya hai"],
     ["new semester kis mahine mein start hota hai"]),
    ("Time Table", "The summer break runs from July to August. The summer semester is optional and used to repeat or improve courses.",
     ["Is there a summer semester?", "summer semester hota hai kya", "chhutiyan kab hoti hain"],
     ["garmiyon ki chhutiyon mein subject repeat ho sakta hai"]),

    # ---------- SEMESTER SUBJECTS (BSCS sample) ----------
    ("Semester Subjects", "BSCS Semester 1: Programming Fundamentals, Calculus, Applied Physics, Functional English, Islamic Studies and ICT Fundamentals.",
     ["What subjects are in semester 1?", "pehle semester ke subjects kon se hain", "1st semester courses BSCS"],
     ["semester one mein kya parhaya jata hai"]),
    ("Semester Subjects", "BSCS Semester 2: Object Oriented Programming, Discrete Structures, Linear Algebra, Digital Logic Design, Communication Skills and Pakistan Studies.",
     ["What subjects are in semester 2?", "dusre semester ke subjects kon se hain", "2nd semester courses BSCS"],
     ["semester two ke courses batao"]),
    ("Semester Subjects", "BSCS Semester 3: Data Structures, Database Systems, Computer Organization and Assembly Language, Probability and Statistics and Technical Writing.",
     ["What subjects are in semester 3?", "teesre semester ke subjects kon se hain", "3rd semester courses BSCS"],
     ["semester three mein kaun si subjects hain"]),
    ("Semester Subjects", "BSCS Semester 4: Design and Analysis of Algorithms, Operating Systems, Computer Networks, Theory of Automata and Introduction to Artificial Intelligence.",
     ["What subjects are in semester 4?", "chothe semester ke subjects kon se hain", "4th semester courses BSCS"],
     ["semester four ki subjects"]),
    ("Semester Subjects", "BSCS Semester 5: Software Engineering, Web Engineering, Machine Learning, Information Security and Elective 1.",
     ["What subjects are in semester 5?", "paanchwe semester ke subjects kon se hain", "5th semester courses BSCS"],
     ["semester five mein kya subjects aate hain"]),
    ("Semester Subjects", "BSCS Semester 6: Compiler Construction, Artificial Intelligence, Mobile App Development, Human Computer Interaction and Elective 2.",
     ["What subjects are in semester 6?", "chhathe semester ke subjects kon se hain", "6th semester courses BSCS"],
     ["semester six ki courses ki list"]),
    ("Semester Subjects", "BSCS Semester 7: Final Year Project 1, Parallel and Distributed Computing, Professional Ethics, Elective 3 and Elective 4.",
     ["What subjects are in semester 7?", "satwe semester ke subjects kon se hain", "7th semester courses BSCS"],
     ["semester seven mein kya hota hai"]),
    ("Semester Subjects", "BSCS Semester 8: Final Year Project 2, Entrepreneurship, Elective 5 and Elective 6.",
     ["What subjects are in semester 8?", "aathwe semester ke subjects kon se hain", "last semester courses BSCS"],
     ["akhri semester mein kya parhna hota hai"]),
    ("Semester Subjects", "BSAI core courses after the shared first two semesters include Machine Learning, Deep Learning, Natural Language Processing, Computer Vision, Data Mining and Big Data.",
     ["What subjects are in BSAI?", "BSAI ke subjects kon se hain", "AI degree ke courses kya hain"],
     ["artificial intelligence program mein kaun si courses parhte hain"]),
    ("Semester Subjects", "Electives start from semester 5. Examples: Deep Learning, Cloud Computing, Data Science, Game Development and Cyber Security.",
     ["What electives are available?", "electives kaun se hain", "elective subjects kab shuru hote hain"],
     ["optional subjects ki list"]),
    ("Semester Subjects", "The Final Year Project (FYP) is done in semesters 7 and 8 in groups of 2 to 3 students under a supervisor.",
     ["What is FYP?", "final year project kya hota hai", "FYP group mein hota hai ya akele"],
     ["fyp ke baray mein batao"]),

    # ---------- RANKING ----------
    ("Ranking", "The university is recognized by the Higher Education Commission (HEC) of Pakistan and its computing programs are NCEAC accredited. For the latest ranking check the HEC and QS ranking websites.",
     ["What is the university ranking?", "university ki ranking kya hai", "kya university HEC recognized hai", "degree HEC se approved hai", "ranking of the university in Pakistan"],
     ["kya yeh uni mustanad hai"]),

    # ---------- LABS AND LIBRARY ----------
    ("Labs", "Labs: computer labs with 40 PCs each, an AI and Machine Learning lab with GPU workstations, a networking lab, an electronics lab and a physics lab. Labs are open from 8:30 AM to 5 PM.",
     ["What labs does the university have?", "university mein labs kaun si hain", "computer labs ki facilities", "AI lab hai kya", "GPU lab available hai"],
     ["yahan kaun si laboratories hain"]),
    ("Labs", "Students can use the labs after class hours with permission from the lab incharge.",
     ["Can I use the lab after class?", "class ke baad lab use kar sakte hain", "lab ka time kya hai"],
     ["classes ke baad lab mein kaam karna ho to"]),
    ("Labs", "Campus Wi-Fi is free for students. Log in with your student ID and portal password.",
     ["Is there Wi-Fi on campus?", "university mein wifi hai", "internet ki facility hai kya"],
     ["kya campus mein free internet milta hai"]),
    ("Labs", "The library is open from 8 AM to 8 PM with books, journals, digital resources and a silent study hall.",
     ["Does the university have a library?", "library ka time kya hai", "library mein kya kya hai"],
     ["kitabon ke liye library kab khulti hai"]),

    # ---------- CAFES ----------
    ("Cafes", "The campus has a main cafeteria and two food courts. Meals cost around PKR 250 to 600. Cafes are open from 8 AM to 6 PM.",
     ["Is there a cafe in the university?", "university mein cafe hai", "canteen kahan hai", "khana kaisa milta hai", "food options on campus"],
     ["kya yahan khane peene ki jagah hai"]),

    # ---------- CAMPUS ENVIRONMENT ----------
    ("Campus Environment", "The campus is green with open study areas, a sports ground, a mosque and student lounges. Security guards and CCTV cover the campus 24 hours.",
     ["What is the campus environment like?", "university ka mahol kaisa hai", "campus kaisa hai", "is the campus safe"],
     ["uni ka environment aur security kaisi hai"]),
    ("Campus Environment", "Student societies include the Computer Society, Debating Society, Sports Society and Drama and Arts Society. Events and tech fests are held every semester.",
     ["Are there student societies?", "societies hain university mein", "extra curricular activities kya hain", "events aur fests hote hain"],
     ["co curricular activities ke liye kya options hain"]),
    ("Campus Environment", "Sports facilities: cricket ground, football field, basketball court, badminton hall and a gym. The annual sports week is held in spring.",
     ["What sports facilities are available?", "sports ki facilities kya hain", "gym hai kya"],
     ["khelne ke liye kya grounds hain"]),
    ("Campus Environment", "Students must wear decent formal or traditional dress and carry their ID card on campus.",
     ["Is there a dress code?", "dress code kya hai"],
     ["kaise kapde pehen kar aana hai"]),

    # ---------- TRANSPORT ----------
    ("Transport", "University buses run on 8 main routes in the city. The transport fee is PKR 8000 per semester. Routes are listed on the website.",
     ["Is there university transport?", "bus service hai kya", "transport fee kitni hai", "pick and drop ki facility"],
     ["ghar se uni aane ke liye bus mil jati hai"]),

    # ---------- HOSTEL / SCHOLARSHIP EXTRAS ----------
    ("Hostel", "Hostel fee is PKR 20000 per month including mess. A refundable security deposit of PKR 10000 is taken at admission.",
     ["What is the hostel fee?", "hostel ki fee kitni hai", "hostel ka kharcha kitna hai"],
     ["hostel mein rehne ka mahana kharcha"]),
    ("Scholarships", "Need based scholarships cover 25 to 100 percent of tuition. Apply on the portal with an income certificate in the first month of the semester.",
     ["How do I apply for a need based scholarship?", "need based scholarship kaise milti hai"],
     ["gareeb talba ke liye financial aid kaise milti hai"]),
    ("Scholarships", "Hafiz-e-Quran students get a 25 percent tuition discount. Government programs such as Ehsaas and the HEC Need Based Scholarship are supported. Submit documents to the scholarship office.",
     ["Is there a scholarship for hafiz students?", "hafiz-e-quran discount milta hai", "Ehsaas scholarship mil sakti hai"],
     ["hafiz ko fee mein rayat"]),

    # ---------- ATTENDANCE AND LEAVE ----------
    ("Attendance and Leave", "Apply for leave through the student portal or the department office before the absence. Medical leave needs a doctor's certificate.",
     ["How do I apply for leave?", "chhutti ki application kaise dein", "leave policy kya hai"],
     ["class se absent hona ho to kya karun"]),
    ("Attendance and Leave", "A semester can be frozen once with the dean's approval for a valid reason. Apply within the first 3 weeks. The paid fee is not refunded.",
     ["Can I freeze my semester?", "semester freeze kaise karte hain", "ek semester ki chhutti le sakte hain"],
     ["parhai rok ke baad mein wapas aa sakta hoon"]),

    # ---------- DOCUMENTS ----------
    ("Documents", "Transcript requests are submitted to the exam office with a fee of PKR 1500. The transcript is ready in 5 working days.",
     ["How can I get my transcript?", "transcript kaise banwate hain", "transcript ki fee kitni hai"],
     ["result card ki copy chahiye"]),
    ("Documents", "The degree is issued within 3 months after all requirements and clearance are complete. Collect it from the exam office or at the convocation.",
     ["When will I get my degree?", "degree kab milti hai", "degree ke liye clearance kya hai"],
     ["graduation ke baad degree haath mein kab aati hai"]),
    ("Documents", "The student ID card is issued within 2 weeks of admission. A lost card can be replaced for PKR 500 with an application to the student affairs office.",
     ["How do I get a student ID card?", "ID card kab milta hai", "card kho jaye to kya karein"],
     ["student card gum ho gaya hai"]),

    # ---------- IT SERVICES ----------
    ("IT Services", "To reset the portal password use Forgot Password on the login page, or visit the IT office with your ID card.",
     ["I forgot my portal password", "portal ka password bhool gaya", "password reset kaise karein"],
     ["student portal mein login nahi ho raha password yaad nahi"]),
    ("IT Services", "Every student gets a university email address like rollnumber@university.edu.pk after admission. Details are on the student portal.",
     ["Do students get a university email?", "uni ka email kaise milta hai", "student email id kya hoti hai"],
     ["university wali email id kahan se banegi"]),
    ("IT Services", "Free student licenses for tools like Microsoft Office and the GitHub Student Developer Pack are arranged by the IT office.",
     ["Do students get free software?", "free software licenses milte hain", "Office 365 free hai"],
     ["student ke liye free tools"]),
    ("IT Services", "The university uses an LMS for lecture slides, assignments and quizzes. Classes are on campus. Online classes happen only in emergencies.",
     ["Are classes online?", "online classes hoti hain", "LMS kya hai"],
     ["slides aur assignments kahan upload hote hain"]),

    # ---------- LIBRARY ----------
    ("Library", "Students can borrow 3 books for 14 days. The late return fine is PKR 10 per day per book.",
     ["How many books can I issue?", "library se kitni kitabein mil sakti hain", "kitab late wapas karne ka jurmana"],
     ["library se book kitne din ke liye mil jati hai"]),
    ("Library", "Students get free access to the HEC digital library with thousands of journals and e-books, from campus and from home with a login.",
     ["Is there a digital library?", "online journals kahan se milenge", "HEC digital library access"],
     ["research papers parhne ke liye online resource"]),

    # ---------- CAREER ----------
    ("Career", "The career counseling office offers CV workshops and mock interviews, and arranges an annual job fair with many companies.",
     ["Does the university help with jobs?", "placement ka system hai", "career counseling milti hai"],
     ["degree ke baad naukri dilwane mein uni madad karti hai"]),
    ("Career", "An internship of 6 to 8 weeks is required for the BS degree, usually in the summer after semester 6. The career office helps find placements.",
     ["Is internship compulsory?", "internship zaroori hai", "internship kab karni hoti hai"],
     ["degree ke dauran training lazmi hai"]),
    ("Career", "The university hosts hackathons, coding contests and project exhibitions every year. The Computer Society announces them on notice boards and social media.",
     ["Are there coding competitions?", "hackathon hota hai", "programming contests hote hain"],
     ["tech events aur projects ki nomaish"]),

    # ---------- CAMPUS FACILITIES ----------
    ("Campus Facilities", "A medical center on campus offers first aid and a doctor from 9 AM to 3 PM. Emergencies are referred to a nearby hospital.",
     ["Is there a medical facility?", "campus mein doctor hai", "dispensary kahan hai"],
     ["tabiyat kharab ho to uni mein ilaj"]),
    ("Campus Facilities", "There are separate prayer areas for male and female students. The main mosque is near Block A and Jumma prayer is held on campus.",
     ["Is there a prayer area?", "namaz ki jagah hai", "mosque on campus"],
     ["jumma ki namaz kahan hoti hai"]),
    ("Campus Facilities", "Student parking is free for bikes and cars with a parking sticker from the security office.",
     ["Is parking available?", "bike parking ki jagah hai", "parking sticker kaise milta hai"],
     ["gaari khari karne ki facility"]),
    ("Campus Facilities", "Female students have a separate common room, a girls hostel with 24 hour security and female staff in the admission office.",
     ["What facilities are there for girls?", "larkiyon ke liye kya facilities hain", "girls common room hai"],
     ["talibat ke liye alag intizam"]),
    ("Campus Facilities", "A free counseling service is available on campus by appointment for study, stress and personal issues.",
     ["Is counseling available?", "counselor se mil sakte hain", "student support service hai"],
     ["pareshani ho to kisi se baat karni ho"]),
    ("Campus Facilities", "Complaints can be submitted to the student affairs office, the complaint box or the portal. They are answered within 7 working days.",
     ["How can I file a complaint?", "shikayat kahan karein", "student affairs office kahan hai"],
     ["kisi masle ki shikayat ka tareeqa"]),

    # ---------- ACADEMICS ----------
    ("Academics", "Faculty includes PhD holders from local and foreign universities. The full list with emails is on each department page.",
     ["Who are the teachers?", "faculty qualified hai", "teachers ka contact kahan se milega"],
     ["asataza ki qualification kya hai"]),
    ("Academics", "Plagiarism above 20 percent in assignments, reports or the FYP thesis is not accepted. Submissions are checked with Turnitin.",
     ["What is the plagiarism policy?", "plagiarism ki limit kitni hai", "Turnitin check hota hai"],
     ["copy paste ki hui report ka kya hoga"]),
]

rows, tests, next_id = [], [], 1
for cat, ans, qs, ts in DATA:
    first_id = next_id                       # is jawab ka pehla id (test ke liye expected_id)
    for q in qs:
        rows.append([next_id, cat, q, ans])  # har paraphrase = ek row, jawab same
        next_id += 1
    for t in ts:
        tests.append([t, first_id])          # test sawal -> sahi jawab ka id

# csv.writer commas aur quotes khud handle karta hai
with open(BASE / "data" / "faqs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "category", "question", "answer"])
    w.writerows(rows)

with open(BASE / "data" / "test_cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "expected_id"])
    w.writerows(tests)

print(f"FAQ rows: {len(rows)} | Unique answers: {len(DATA)} | Test questions: {len(tests)}")
