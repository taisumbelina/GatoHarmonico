import datetime
import re
import logging
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    ReminderScheduled,
    SlotSet,
    ActiveLoop,
    ReminderCancelled,
    FollowupAction
)
from rasa_sdk.types import DomainDict

_ = DomainDict # Silencia o aviso do Pylance para DomainDict

logger = logging.getLogger(__name__)

# Helper function for RG formatting
def format_rg(rg_number: str) -> str:
    """Formata um número de RG para um formato de exibição comum brasileiro (ex: XX.XXX.XXX-X)."""
    clean_rg = re.sub(r'[^0-9A-Z]', '', rg_number).upper()
    
    if len(clean_rg) == 9: 
        if clean_rg.isdigit() or clean_rg[-1] == 'X':
            return f"{clean_rg[0:2]}.{clean_rg[2:5]}.{clean_rg[5:8]}-{clean_rg[8]}"
    elif len(clean_rg) == 8: 
        return f"{clean_rg[0:2]}.{clean_rg[2:5]}.{clean_rg[5:7]}-{clean_rg[7]}"
    return clean_rg


# --- Ações de Lembrete ---
class ActionScheduleInactivityReminder(Action):
    def name(self) -> Text:
        return "action_schedule_inactivity_reminder"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance se não forem usados explicitamente de outra forma.
        _ = dispatcher
        _ = tracker
        _ = domain
        trigger_time = datetime.datetime.now() + datetime.timedelta(minutes=2)
        logger.debug(f"Lembrete de inatividade agendado para: {trigger_time}")
        return [
            ReminderScheduled(
                "EXTERNAL_inactivity_reminder",
                trigger_date_time=trigger_time,
                name="inactivity_reminder",
                kill_on_user_message=True,
            )
        ]

class ActionReactToInactivityReminder(Action):
    def name(self) -> Text:
        return "action_react_to_inactivity_reminder"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.info("Lembrete de inatividade acionado. Enviando mensagem.")
        dispatcher.utter_message(response="utter_inactivity_reminder")
        return []

class ActionDeactivateForm(Action):
    def name(self) -> Text:
        return "action_deactivate_form"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.debug("Desativando formulário e limpando requested_slot.")
        return [SlotSet("requested_slot", None), ActiveLoop(None)]

class ActionForgetReminders(Action):
    def name(self) -> Text:
        return "action_forget_reminders"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.debug("ActionForgetReminders: Cancelando lembretes e resetando flags e slots de agendamento.")
        return [
            ReminderCancelled(name="inactivity_reminder"),
            SlotSet("dados_pessoais_confirmados_pendente", False),
            SlotSet("data_agendamento", None),
            SlotSet("hora_agendamento", None)
            # SlotSet("preco_servico", None) # Comentado para não limpar o preço antes da confirmação final
        ]

class ActionStartAulaAgendamento(Action):
    def name(self) -> Text:
        return "action_start_aula_agendamento"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        instrumento_slot_value = tracker.get_slot("instrumentos")
        instrumento_val = None
        if isinstance(instrumento_slot_value, list) and instrumento_slot_value:
            instrumento_val = instrumento_slot_value[0]
        elif isinstance(instrumento_slot_value, str) and instrumento_slot_value:
            instrumento_val = instrumento_slot_value

        logger.debug(f"ActionStartAulaAgendamento: Instrumento atual: {instrumento_val}")
        events = []
        events.append(ReminderScheduled(
                "EXTERNAL_inactivity_reminder",
                trigger_date_time=datetime.datetime.now() + datetime.timedelta(minutes=2),
                name="inactivity_reminder",
                kill_on_user_message=True,
            ))

        if not instrumento_val:
            dispatcher.utter_message(response="utter_ask_instrumento_aula")
        else:
            servico_nome = f"Aula de {instrumento_val.capitalize()}"
            preco = 90.0
            events.append(SlotSet("servico_escolhido", servico_nome))
            events.append(SlotSet("preco_servico", preco))
            logger.debug(f"Slots definidos: servico_escolhido='{servico_nome}', preco_servico={preco}")
            dispatcher.utter_message(response="utter_ask_modo_agendamento")
        return events

class ActionSetConsultoriaDetails(Action):
    def name(self) -> Text:
        return "action_set_consultoria_details"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        servico_nome = "Consultoria Musical"
        preco = 120.0
        logger.debug(f"ActionSetConsultoriaDetails: Definindo servico_escolhido='{servico_nome}', preco_servico={preco}")
        return [
            SlotSet("servico_escolhido", servico_nome),
            SlotSet("preco_servico", preco)
        ]

class ActionInformarPrecoAula(Action):
    def name(self) -> Text:
        return "action_informar_preco_aula"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        instrumentos_slot = tracker.get_slot("instrumentos")
        instrumento_mencionado = None
        events = []

        if isinstance(instrumentos_slot, list) and instrumentos_slot:
            instrumento_mencionado = instrumentos_slot[0]
        elif isinstance(instrumentos_slot, str) and instrumentos_slot:
            instrumento_mencionado = instrumentos_slot

        if not instrumento_mencionado:
            latest_entities = tracker.latest_message.get("entities", [])
            for entity in latest_entities:
                if entity.get("entity") == "instrumentos":
                    instrumento_mencionado = entity.get("value")
                    events.append(SlotSet("instrumentos", instrumento_mencionado))
                    break

        if instrumento_mencionado:
            instrumento_formatado = instrumento_mencionado.capitalize()
            logger.debug(f"ActionInformarPrecoAula: Instrumento mencionado: {instrumento_formatado}")
            dispatcher.utter_message(response="utter_informar_preco_aula_especifica", instrumentos=instrumento_formatado)
        else:
            dispatcher.utter_message(response="utter_informar_preco_aula_geral")
        return events

class ActionHandleCompraInstrumento(Action):
    def name(self) -> Text:
        return "action_handle_compra_instrumento"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        instrumento_slot = tracker.get_slot("instrumentos")
        instrumento_val = None
        if isinstance(instrumento_slot, list) and instrumento_slot:
            instrumento_val = instrumento_slot[0]
        elif isinstance(instrumento_slot, str) and instrumento_slot:
            instrumento_val = instrumento_slot
        
        # Silencia o aviso do Pylance para 'instrumento_slot' aqui
        _ = instrumento_slot 

        logger.debug(f"ActionHandleCompraInstrumento: Instrumento atual: {instrumento_val}")
        events = []
        if not instrumento_val:
            latest_intent = tracker.latest_message.get("intent", {}).get("name")
            if latest_intent == "compra_instrumento":
                latest_entities = tracker.latest_message.get("entities", [])
                for entity in latest_entities:
                    if entity.get("entity") == "instrumentos":
                        instrumento_val = entity.get("value")
                        events.append(SlotSet("instrumentos", instrumento_val))
                        break
        if instrumento_val:
            logger.debug(f"ActionHandleCompraInstrumento: Instrumento para compra: {instrumento_val}")
            dispatcher.utter_message(response="utter_compra_instrumento_especifico", instrumentos=instrumento_val.capitalize())
        else:
            dispatcher.utter_message(response="utter_compra_instrumento")

        events.append(ReminderScheduled(
                "EXTERNAL_inactivity_reminder",
                trigger_date_time=datetime.datetime.now() + datetime.timedelta(minutes=2),
                name="inactivity_reminder",
                kill_on_user_message=True,
            ))
        return events

class ActionResetPersonalDataSlots(Action):
    def name(self) -> Text:
        return "action_reset_personal_data_slots"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Acessa 'dispatcher', 'tracker' e 'domain' para silenciar os avisos do Pylance
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.debug("ActionResetPersonalDataSlots: Limpando slots do formulário, agendamento e flag de confirmação.")
        return [
            SlotSet("nome", None),
            SlotSet("cpf", None),
            SlotSet("rg", None),
            SlotSet("rg_display", None), # Adicionado reset para rg_display
            SlotSet("data_nascimento", None),
            SlotSet("dados_pessoais_confirmados_pendente", False),
            SlotSet("data_agendamento", None),
            SlotSet("hora_agendamento", None),
            # Trigger the personal data form again immediately
            FollowupAction("personal_data_form")
        ]

class ValidatePersonalDataForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_personal_data_form"

    async def validate_nome(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        _ = dispatcher
        _ = domain
        logger.debug(f"Validando nome. Valor do slot: '{slot_value}'")
        
        # Tenta obter o nome completo a partir da entidade 'nome' se ela foi extraída.
        # Usa o último valor da entidade, caso haja múltiplas.
        nome_from_entity = next(
            (entity.get("value") for entity in reversed(tracker.latest_message.get("entities", [])) if entity.get("entity") == "nome"),
            None
        )

        # Se a entidade 'nome' foi extraída e parece um nome completo, usa-a.
        # Caso contrário, tenta usar o 'slot_value' fornecido.
        value_to_validate = nome_from_entity if nome_from_entity and len(nome_from_entity.split()) >= 2 else str(slot_value).strip()
        
        # Último recurso: se o nome ainda for muito curto ou não foi extraído da entidade,
        # tenta usar a mensagem completa do usuário como nome, se ela tiver pelo menos 2 palavras.
        if not value_to_validate or len(value_to_validate.split()) < 2:
            dispatcher.utter_message(text="Por favor, digite seu nome completo (pelo menos nome e sobrenome).")
            return {"nome": None}
        
        # Validação principal: deve ter pelo menos duas palavras (nome e sobrenome)
        if len(value_to_validate.split()) < 2:
            dispatcher.utter_message(text="Por favor, digite seu nome completo (pelo menos nome e sobrenome).")
            return {"nome": None}
        
        # Verifica se há caracteres inválidos no nome.
        if not re.fullmatch(r"^[a-zA-ZÀ-ÖØ-öø-ÿ\s'\-´`~^çÇ.]+$", value_to_validate):
            dispatcher.utter_message(text="Por favor, digite apenas caracteres válidos no nome.")
            return {"nome": None}
        
        # Normaliza a capitalização do nome (Primeira Letra Maiúscula de Cada Palavra)
        formatted_name = " ".join([part.capitalize() for part in value_to_validate.split()])
        
        logger.info(f"Nome '{formatted_name}' validado com sucesso.")
        return {"nome": formatted_name}

    async def validate_cpf(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.debug(f"Validando CPF. Valor do slot: '{slot_value}'")
        
        user_input_text = str(slot_value).strip()

        if not user_input_text:
            dispatcher.utter_message(text="Por favor, informe seu CPF.")
            return {"cpf": None}
        
        cpf_regex_pattern = re.compile(r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$')
        
        if not cpf_regex_pattern.fullmatch(user_input_text):
            dispatcher.utter_message(text="CPF inválido. Por favor, informe um CPF com 11 dígitos válidos (apenas números ou no formato XXX.XXX.XXX-XX).")
            return {"cpf": None}
        
        cleaned_cpf = re.sub(r'[^0-9]', '', user_input_text)
        
        if len(set(cleaned_cpf)) == 1:
            dispatcher.utter_message(text="CPF inválido (todos os dígitos iguais). Por favor, informe um CPF válido.")
            return {"cpf": None}

        logger.info(f"CPF '{cleaned_cpf}' validado com sucesso.")
        return {"cpf": cleaned_cpf}


    async def validate_rg(
            self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
        ) -> Dict[Text, Any]:
            _ = dispatcher
            _ = tracker
            _ = domain
            logger.debug(f"Validando RG. Valor do slot: '{slot_value}'")

            user_input_text = str(slot_value).strip()

            if not user_input_text:
                dispatcher.utter_message(text="Por favor, informe seu RG.")
                return {"rg": None, "rg_display": None}
            
            # Regex para RG mais robusta, permitindo formatos comuns e o 'X' no final
            # Agora permite que o usuário digite sem pontuação também
            rg_regex_pattern = re.compile(r'^\d{1,2}\.?\d{3}\.?\d{3}-?[\dX]$')

            if not rg_regex_pattern.fullmatch(user_input_text):
                dispatcher.utter_message(text="RG inválido. Por favor, informe um RG válido (Ex: 12.345.678-9 ou apenas números).")
                return {"rg": None, "rg_display": None}
            
            cleaned_rg = re.sub(r'[^\dX]', '', user_input_text).upper()
            
            # Formata o RG para exibição com pontuação usando a função helper
            formatted_rg_display = format_rg(cleaned_rg)
            
            logger.info(f"RG '{cleaned_rg}' (display: '{formatted_rg_display}') validado com sucesso.")
            return {"rg": cleaned_rg, "rg_display": formatted_rg_display} # Retorna o RG limpo e o formatado para display


    async def validate_data_nascimento(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        _ = dispatcher
        _ = tracker
        _ = domain
        logger.debug(f"Validando data_nascimento. Valor do slot: {slot_value}, tipo: {type(slot_value)}")
        if not slot_value:
            dispatcher.utter_message(text="Por favor, informe sua data de nascimento.")
            return {"data_nascimento": None}
        date_input_value = str(slot_value)
        parsed_date = None
        possible_formats = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
        for fmt in possible_formats:
            try:
                parsed_date = datetime.datetime.strptime(date_input_value, fmt).date()
                break
            except ValueError:
                continue
        if not parsed_date:
            try:
                iso_date_part = date_input_value.split("T")[0]
                parsed_date = datetime.datetime.fromisoformat(iso_date_part).date()
            except ValueError:
                dispatcher.utter_message(text="Formato de data inválido. Por favor, digite no formato DD/MM/AAAA.")
                return {"data_nascimento": None}
        
        current_date = datetime.date.today()
        # Ajustado o limite inferior da idade para 130 anos para ser mais flexível,
        # e o limite superior para garantir que não seja no futuro ou muito recente (menor de 5 anos)
        min_date = current_date - datetime.timedelta(days=130*365.25)
        max_recent_date = current_date - datetime.timedelta(days=5*365.25) # Nascido há pelo menos 5 anos

        if parsed_date > current_date or parsed_date < min_date or parsed_date > max_recent_date:
            dispatcher.utter_message(text="Data de nascimento inválida (muito no futuro, muito antiga ou muito recente). Use DD/MM/AAAA.")
            return {"data_nascimento": None}
        formatted_date_str = parsed_date.strftime("%d/%m/%Y")
        logger.info(f"Data de nascimento 		'{formatted_date_str}' validada.")

        # *** INÍCIO DA ALTERAÇÃO: Disparar confirmação após validar o último slot ***
        # Obtém os valores dos outros slots necessários do formulário
        nome = tracker.get_slot("nome")
        cpf = tracker.get_slot("cpf")
        rg_display = tracker.get_slot("rg_display") # Usar rg_display para confirmação

        # Verifica se todos os slots necessários estão preenchidos
        if nome and cpf and rg_display and formatted_date_str:
            logger.info("Todos os dados pessoais preenchidos. Disparando confirmação.")
            # Envia a mensagem de confirmação usando os slots preenchidos
            dispatcher.utter_message(response="utter_confirm_personal_data",
                                    nome=nome,
                                    cpf=cpf,
                                    rg_display=rg_display,
                                    data_nascimento=formatted_date_str)
            # Define um slot para indicar que a confirmação está pendente
            # Isso pode ser usado nas regras para direcionar o fluxo
            return {"data_nascimento": formatted_date_str, "dados_pessoais_confirmados_pendente": True}
        else:
            # Se algum slot ainda estiver faltando (não deveria acontecer se a lógica do form estiver correta)
            # apenas retorna o slot validado.
            logger.warning("validate_data_nascimento: Tentando confirmar, mas nem todos os slots estão preenchidos.")
            return {"data_nascimento": formatted_date_str}
        # *** FIM DA ALTERAÇÃO ***
class ActionExtractAndConfirmData(Action):
    def name(self) -> Text:
        return "action_extract_and_confirm_data"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        _ = dispatcher
        _ = tracker
        _ = domain
        nome = tracker.get_slot("nome")
        cpf_raw = tracker.get_slot("cpf")
        rg_raw = tracker.get_slot("rg")
        data_nascimento = tracker.get_slot("data_nascimento")
        logger.debug(f"ActionExtractAndConfirmData: Slots: nome={nome}, cpf={cpf_raw}, rg={rg_raw}, data_nascimento={data_nascimento}")
        if not all([nome, cpf_raw, rg_raw, data_nascimento]):
            missing_slots_text = []
            if not nome: missing_slots_text.append("nome completo")
            if not cpf_raw: missing_slots_text.append("CPF")
            if not rg_raw: missing_slots_text.append("RG")
            if not data_nascimento: missing_slots_text.append("data de nascimento")
            dispatcher.utter_message(text=f"Ops, parece que alguns dados ainda estão faltando: {', '.join(missing_slots_text)}. Vamos tentar de novo.")
            return [FollowupAction("personal_data_form")]
        
        # Formata CPF para exibição
        formatted_cpf = f"{cpf_raw[:3]}.{cpf_raw[3:6]}.{cpf_raw[6:9]}-{cpf_raw[9:]}" if cpf_raw and len(cpf_raw) == 11 else cpf_raw
        
        # Formata RG para exibição com pontuação (XX.XXX.XXX-X ou XXX.XXX.XX-X)
        formatted_rg = rg_raw
        if rg_raw:
            formatted_rg = format_rg(rg_raw) # Usa a função helper para formatar o RG

        dispatcher.utter_message(
            response="utter_confirm_personal_data",
            nome=nome,
            cpf=formatted_cpf,
            rg_display=formatted_rg, # Passa o RG formatado para o placeholder rg_display
            data_nascimento=data_nascimento
        )
        return [SlotSet("dados_pessoais_confirmados_pendente", True)]


class ActionProcessAgendamentoDate(Action):
    def name(self) -> Text:
        return "action_process_agendamento_date"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        _ = dispatcher
        _ = tracker
        _ = domain
        today = datetime.date.today()
        entities = tracker.latest_message.get('entities', [])
        user_input_text = tracker.latest_message.get('text', '').lower().strip()
        logger.debug(f"ActionProcessAgendamentoDate: Input: '{user_input_text}', Entidades: {entities}")
        date_to_set = None
        time_to_set = None # Adicionado para capturar a hora

        for entity in entities:
            if entity.get('entity') == 'time' and entity.get('extractor') == 'DucklingEntityExtractor':
                try:
                    duckling_value = entity.get('value')
                    if isinstance(duckling_value, dict) and 'value' in duckling_value:
                        iso_string = duckling_value['value']
                    elif isinstance(duckling_value, str):
                        iso_string = duckling_value
                    else:
                        logger.warning(f"Duckling 'time' entity value unexpected format: {duckling_value}")
                        continue

                    # Tenta extrair a data do ISO string para validação de passado
                    parsed_iso_datetime = datetime.datetime.fromisoformat(iso_string)
                    parsed_iso_date = parsed_iso_datetime.date()
                    
                    # Formata a hora para o formato desejado (ex: "14:30" ou "14h")
                    # Prioriza o formato com minutos se existirem, senão usa 'h'
                    if parsed_iso_datetime.minute == 0:
                        time_to_set = parsed_iso_datetime.strftime("%Hh")
                    else:
                        time_to_set = parsed_iso_datetime.strftime("%H:%M")

                    if parsed_iso_date < today:
                        # Se a data for no passado, tenta ajustar para o futuro (próxima ocorrência)
                        if not any(kw in user_input_text for kw in ["próxima", "proxima", "que vem", "ano que vem"]):
                            # Se for o mesmo dia da semana mas no passado, avança 7 dias
                            if parsed_iso_date.weekday() < today.weekday() and parsed_iso_date.isocalendar()[1] == today.isocalendar()[1] :
                                parsed_iso_date += datetime.timedelta(days=7)
                            elif parsed_iso_date < today : # Qualquer outra data no passado que não foi tratada
                                dispatcher.utter_message(text=f"Miau... a data '{parsed_iso_date.strftime('%d/%m/%Y')}' está no passado. Poderia informar uma data futura?")
                                return [SlotSet("data_agendamento", None), SlotSet("hora_agendamento", None)] # Limpa ambos
                    
                    date_to_set = parsed_iso_date.strftime("%d/%m/%Y")
                    logger.info(f"ActionProcessAgendamentoDate: Data Duckling '{iso_string}' -> '{date_to_set}', Hora: '{time_to_set}'")
                    return [SlotSet("data_agendamento", date_to_set), SlotSet("hora_agendamento", time_to_set)]
                except Exception as e:
                    logger.warning(f"Erro ao processar entidade Duckling '{entity.get('value')}': {e}")
            
            elif entity.get('entity') == 'date' and entity.get('extractor') == 'DucklingEntityExtractor':
                try:
                    duckling_value = entity.get('value')
                    if isinstance(duckling_value, dict) and 'value' in duckling_value:
                        iso_string = duckling_value['value']
                    elif isinstance(duckling_value, str):
                        iso_string = duckling_value
                    else:
                        logger.warning(f"Duckling 'date' entity value unexpected format: {duckling_value}")
                        continue

                    parsed_iso_date = datetime.datetime.fromisoformat(iso_string.split("T")[0]).date()

                    if parsed_iso_date < today:
                        if not any(kw in user_input_text for kw in ["próxima", "proxima", "que vem", "ano que vem"]):
                            if parsed_iso_date.weekday() < today.weekday() and parsed_iso_date.isocalendar()[1] == today.isocalendar()[1]:
                                parsed_iso_date += datetime.timedelta(days=7)
                            elif parsed_iso_date < today:
                                dispatcher.utter_message(text=f"Miau... a data '{parsed_iso_date.strftime('%d/%m/%Y')}' está no passado. Poderia informar uma data futura?")
                                return [SlotSet("data_agendamento", None), SlotSet("hora_agendamento", None)] # Limpa ambos

                    date_to_set = parsed_iso_date.strftime("%d/%m/%Y")
                    logger.info(f"ActionProcessAgendamentoDate: Data Duckling (date entity) '{iso_string}' -> '{date_to_set}'")
                    # Se apenas a data foi encontrada, a hora ainda não foi definida aqui.
                    return [SlotSet("data_agendamento", date_to_set)]
                except Exception as e:
                    logger.warning(f"Erro ao processar entidade Duckling '{entity.get('value')}': {e}")
        
        # Fallback se Duckling não encontrar ou falhar para DATA
        # Este bloco só será executado se nenhuma entidade 'time' ou 'date' do Duckling foi processada e retornou.
        if not date_to_set:
            date_entity_value = None
            for entity in entities:
                if entity.get('entity') == 'date':
                    date_entity_value = entity.get('value')
                    break
            
            text_for_date_parse = date_entity_value if date_entity_value else user_input_text

            if "hoje" in text_for_date_parse:
                date_to_set = today.strftime("%d/%m/%Y")
            elif "amanhã" in text_for_date_parse or "amanha" in text_for_date_parse:
                date_to_set = (today + datetime.timedelta(days=1)).strftime("%d/%m/%Y")
            else:
                match_date = re.search(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", text_for_date_parse)
                if match_date:
                    day = int(match_date.group(1))
                    month = int(match_date.group(2))
                    year_str = match_date.group(3)
                    year_to_use = today.year
                    if year_str:
                        year_to_use = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
                    try:
                        prospective_date = datetime.date(year_to_use, month, day)
                        if not year_str and prospective_date < today:
                            prospective_date = datetime.date(today.year + 1, month, day)
                        elif prospective_date < today:
                            dispatcher.utter_message(text=f"Miau... a data '{prospective_date.strftime('%d/%m/%Y')}' está no passado. Poderia informar uma data futura?")
                            return [SlotSet("data_agendamento", None), SlotSet("hora_agendamento", None)]
                        date_to_set = prospective_date.strftime("%d/%m/%Y")
                    except ValueError:
                        logger.warning(f"Data DD/MM/YYYY inválida (fallback regex match): {day}/{month}/{year_to_use}")
                else:
                    days_of_week_map = {"segunda":0,"terça":1,"terca":1,"quarta":2,"quinta":3,"sexta":4,"sábado":5,"sabado":5,"domingo":6}
                    target_day_index = None
                    is_proxima = any(kw in user_input_text for kw in ["próxima", "proxima", "que vem", "ano que vem"])
                    
                    for day_name, day_idx in days_of_week_map.items():
                        if day_name in text_for_date_parse:
                            target_day_index = day_idx
                            break
                    
                    if target_day_index is not None:
                        current_weekday = today.weekday()
                        days_ahead = target_day_index - current_weekday
                        if days_ahead < 0 or (days_ahead == 0 and is_proxima): days_ahead += 7
                        elif days_ahead == 0 and not is_proxima and not ("hoje" in text_for_date_parse):
                            days_ahead += 7
                        date_to_set = (today + datetime.timedelta(days=days_ahead)).strftime("%d/%m/%Y")

        # Fallback para HORA se o Duckling não capturou a hora junto com a data
        if not time_to_set:
            time_entity_value = None
            for entity in entities:
                if entity.get('entity') == 'time':
                    # Pega a entidade de tempo que não foi processada pelo Duckling com a data
                    if entity.get('extractor') != 'DucklingEntityExtractor' or (entity.get('extractor') == 'DucklingEntityExtractor' and 'value' not in entity):
                        time_entity_value = entity.get('value')
                        break
            
            text_for_time_parse = time_entity_value if time_entity_value else user_input_text

            match_time_h = re.search(r"(\d{1,2})h", text_for_time_parse)
            match_time_hm = re.search(r"(\d{1,2}):(\d{2})", text_for_time_parse)

            if match_time_hm:
                hour = int(match_time_hm.group(1))
                minute = int(match_time_hm.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    time_to_set = f"{hour:02d}:{minute:02d}"
            elif match_time_h:
                hour = int(match_time_h.group(1))
                if 0 <= hour <= 23:
                    time_to_set = f"{hour:02d}h"
            elif "meio-dia" in text_for_time_parse or "meio dia" in text_for_time_parse:
                time_to_set = "12h"
            elif "meia noite" in text_for_time_parse or "meia-noite" in text_for_time_parse:
                time_to_set = "00h"
            elif "da manhã" in text_for_time_parse or "de manha" in text_for_time_parse:
                # Se for apenas "de manhã" sem hora específica, talvez pedir mais detalhes ou inferir
                pass # Ou pode ser um slotset de 'periodo_dia'
            elif "da tarde" in text_for_time_parse:
                pass # Ou pode ser um slotset de 'periodo_dia'
            elif "da noite" in text_for_time_parse:
                pass # Ou pode ser um slotset de 'periodo_dia'

        events = []
        if date_to_set:
            events.append(SlotSet("data_agendamento", date_to_set))
        else:
            logger.warning(f"ActionProcessAgendamentoDate: Não foi possível formatar a data de '{user_input_text}'.")
            dispatcher.utter_message(text=f"Miau... não consegui entender a data '{user_input_text}'. Poderia tentar no formato DD/MM/AAAA, ou dizer 'hoje', 'amanhã' ou 'próxima segunda'?")
            return [SlotSet("data_agendamento", None), SlotSet("hora_agendamento", None)] # Retorna aqui se a data não for válida

        if time_to_set:
            events.append(SlotSet("hora_agendamento", time_to_set))
        # Se a hora não foi encontrada, não precisa de uma mensagem de erro específica aqui,
        # pois o formulário irá solicitar a hora posteriormente se for um slot obrigatório.
        
        logger.info(f"ActionProcessAgendamentoDate: Slots resultantes: data_agendamento='{date_to_set}', hora_agendamento='{time_to_set}'")
        return events


class ActionForgetRemindersAndAskDia(Action):
    def name(self) -> Text:
        return "action_forget_reminders_and_ask_dia"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        _ = domain
        _ = tracker
        _ = dispatcher 
        logger.debug("ActionForgetRemindersAndAskDia: Resetando flags e preparando para perguntar o dia.")
        
        # Esta ação agora faz a pergunta e passa o controle
        dispatcher.utter_message(response="utter_ask_dia_agendamento")
        
        return [
            ReminderCancelled(name="inactivity_reminder"),
            SlotSet("dados_pessoais_confirmados_pendente", False),
            SlotSet("data_agendamento", None),
            SlotSet("hora_agendamento", None),
            # Adicionado FollowupAction para garantir que o bot ouça após a fala
            FollowupAction("action_listen")
        ]

class ActionAskDiaAgendamento(Action):
    def name(self) -> Text:
        return "action_ask_dia_agendamento"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        _ = domain
        _ = tracker
        _ = dispatcher 
        # A ação apenas faz a pergunta, o fluxo é controlado pela regra que a chamou
        dispatcher.utter_message(response="utter_ask_dia_agendamento")
        return [
            FollowupAction("action_schedule_inactivity_reminder"),
            FollowupAction("action_listen")
        ]

class ActionConfirmAgendamentoFinal(Action):
    def name(self) -> Text:
        return "action_confirm_agendamento_final"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        nome = tracker.get_slot("nome")
        servico_escolhido = tracker.get_slot("servico_escolhido")
        modo_agendamento = tracker.get_slot("modo_agendamento")
        data_agendamento = tracker.get_slot("data_agendamento")
        hora_agendamento = tracker.get_slot("hora_agendamento")
        preco_servico = tracker.get_slot("preco_servico")
        cpf_raw = tracker.get_slot("cpf")
        rg_display = tracker.get_slot("rg_display") # Usar o slot rg_display
        data_nascimento = tracker.get_slot("data_nascimento")

        # Formata o CPF
        formatted_cpf = "N/A"
        if cpf_raw and len(cpf_raw) == 11:
            formatted_cpf = f"{cpf_raw[:3]}.{cpf_raw[3:6]}.{cpf_raw[6:9]}-{cpf_raw[9:]}"
        elif cpf_raw: # Caso o CPF não tenha 11 dígitos por algum motivo, exibe o que tem
            formatted_cpf = cpf_raw
        
        # Formata o preço com 2 casas decimais e vírgula como separador decimal
        formatted_preco = "N/A"
        if preco_servico is not None:
            # Garante que preco_servico é um float antes de formatar
            try:
                numeric_preco = float(preco_servico)
                formatted_preco = f"{numeric_preco:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            except ValueError:
                logger.warning(f"preco_servico '{preco_servico}' não é um número válido.")
                formatted_preco = "N/A"

        # Utter a mensagem com os valores formatados
        dispatcher.utter_message(
            text=f"Miauravilha! Agendamento confirmado para {nome}!\n"
                f"Sua {servico_escolhido} será {modo_agendamento} no dia {data_agendamento} às {hora_agendamento}.\n"
                f"O valor do serviço é R$ {formatted_preco}.\n"
                f"CPF: {formatted_cpf}, RG: {rg_display}, Nasc.: {data_nascimento}.\n"
                f"Agora, vamos para o pagamento."
        )

        # Limpar os slots de agendamento após a confirmação final
        # Você pode optar por remover ou manter essa limpeza dependendo do seu fluxo pós-pagamento
        return [
            SlotSet("data_agendamento", None),
            SlotSet("hora_agendamento", None),
            SlotSet("servico_escolhido", None), # Limpar após o agendamento completo
            SlotSet("preco_servico", None),     # Limpar após o agendamento completo
            SlotSet("nome", None),
            SlotSet("cpf", None),
            SlotSet("rg", None),
            SlotSet("rg_display", None),
            SlotSet("data_nascimento", None),
            SlotSet("modo_agendamento", None),
            SlotSet("dados_pessoais_confirmados_pendente", False)
        ]