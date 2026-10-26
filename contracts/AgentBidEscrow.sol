// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title AgentBidEscrow
 * @dev Cryptographic escrow smart contract managing task payments and deterministic settlement
 * for the AgentBid AI marketplace.
 *
 * Core Principle: The contract holds funds and enforces explicit state transitions,
 * cryptographic delivery proofs, and deadline-based refund policies.
 */
contract AgentBidEscrow {
    enum TaskState {
        NONE,
        CREATED,
        FUNDED,
        IN_PROGRESS,
        DELIVERED,
        APPROVED,
        DISPUTED,
        SETTLED,
        REFUNDED,
        CANCELLED
    }

    enum DisputeOutcome {
        PAY_AGENT,
        REFUND_CLIENT,
        SPLIT_50_50
    }

    struct Task {
        bytes32 taskId;
        address payable client;
        address payable agent;
        uint256 amount;
        uint256 deadline;
        bytes32 deliverableHash;
        TaskState state;
        bool exists;
    }

    address public immutable owner;
    address public reviewer;

    // Mutex lock for reentrancy defense
    uint256 private _status;
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;

    mapping(bytes32 => Task) public tasks;

    // Events
    event TaskCreated(bytes32 indexed taskId, address indexed client, address indexed agent, uint256 deadline);
    event TaskFunded(bytes32 indexed taskId, address indexed client, uint256 amount);
    event TaskStarted(bytes32 indexed taskId, address indexed agent);
    event TaskDelivered(bytes32 indexed taskId, bytes32 deliverableHash);
    event TaskSettled(bytes32 indexed taskId, address indexed agent, uint256 amount);
    event TaskRefunded(bytes32 indexed taskId, address indexed client, uint256 amount);
    event TaskDisputed(bytes32 indexed taskId, address indexed initiator, bytes32 evidenceHash);
    event DisputeResolved(bytes32 indexed taskId, DisputeOutcome outcome);
    event ReviewerUpdated(address indexed oldReviewer, address indexed newReviewer);

    // Modifiers
    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call");
        _;
    }

    modifier onlyReviewer() {
        require(msg.sender == reviewer, "Only appointed reviewer can call");
        _;
    }

    modifier onlyClient(bytes32 taskId) {
        require(tasks[taskId].client == msg.sender, "Caller is not task client");
        _;
    }

    modifier onlyAgent(bytes32 taskId) {
        require(tasks[taskId].agent == msg.sender, "Caller is not assigned agent");
        _;
    }

    modifier inState(bytes32 taskId, TaskState expected) {
        require(tasks[taskId].state == expected, "Invalid task state for action");
        _;
    }

    constructor(address _reviewer) {
        owner = msg.sender;
        reviewer = _reviewer;
        _status = _NOT_ENTERED;
    }

    function setReviewer(address _newReviewer) external onlyOwner {
        require(_newReviewer != address(0), "Invalid reviewer address");
        emit ReviewerUpdated(reviewer, _newReviewer);
        reviewer = _newReviewer;
    }

    /**
     * @notice Register agreed task parameters before or during funding.
     */
    function createTask(
        bytes32 taskId,
        address payable agent,
        uint256 deadline
    ) external {
        require(!tasks[taskId].exists, "Task already exists");
        require(agent != address(0), "Invalid agent address");
        require(deadline > block.timestamp, "Deadline must be in the future");

        tasks[taskId] = Task({
            taskId: taskId,
            client: payable(msg.sender),
            agent: agent,
            amount: 0,
            deadline: deadline,
            deliverableHash: bytes32(0),
            state: TaskState.CREATED,
            exists: true
        });

        emit TaskCreated(taskId, msg.sender, agent, deadline);
    }

    /**
     * @notice Client deposits ETH into escrow.
     */
    function fundTask(bytes32 taskId) external payable inState(taskId, TaskState.CREATED) {
        Task storage task = tasks[taskId];
        require(msg.sender == task.client, "Only client can fund task");
        require(msg.value > 0, "Funding amount must be greater than zero");

        task.amount = msg.value;
        task.state = TaskState.FUNDED;

        emit TaskFunded(taskId, msg.sender, msg.value);
    }

    /**
     * @notice Agent signals start of work.
     */
    function startWork(bytes32 taskId) external onlyAgent(taskId) inState(taskId, TaskState.FUNDED) {
        tasks[taskId].state = TaskState.IN_PROGRESS;
        emit TaskStarted(taskId, msg.sender);
    }

    /**
     * @notice Agent registers cryptographic proof of delivery (content hash).
     */
    function markDelivered(bytes32 taskId, bytes32 deliverableHash) external onlyAgent(taskId) {
        Task storage task = tasks[taskId];
        require(
            task.state == TaskState.FUNDED || task.state == TaskState.IN_PROGRESS,
            "Task not eligible for delivery"
        );
        require(deliverableHash != bytes32(0), "Empty deliverable hash");

        task.deliverableHash = deliverableHash;
        task.state = TaskState.DELIVERED;

        emit TaskDelivered(taskId, deliverableHash);
    }

    /**
     * @notice Client approves deliverable and releases escrow payment to agent.
     */
    function approveAndPay(bytes32 taskId) external onlyClient(taskId) inState(taskId, TaskState.DELIVERED) nonReentrant {
        Task storage task = tasks[taskId];
        uint256 payout = task.amount;
        require(payout > 0, "No funds in escrow");

        task.amount = 0;
        task.state = TaskState.SETTLED;

        (bool success, ) = task.agent.call{value: payout}("");
        require(success, "Payment transfer failed");

        emit TaskSettled(taskId, task.agent, payout);
    }

    /**
     * @notice Client requests full refund if agent missed the agreed deadline without delivering.
     */
    function requestRefund(bytes32 taskId) external onlyClient(taskId) nonReentrant {
        Task storage task = tasks[taskId];
        require(
            task.state == TaskState.FUNDED || task.state == TaskState.IN_PROGRESS,
            "Task cannot be refunded in current state"
        );
        require(block.timestamp > task.deadline, "Deadline has not passed yet");

        uint256 refundAmount = task.amount;
        require(refundAmount > 0, "No funds to refund");

        task.amount = 0;
        task.state = TaskState.REFUNDED;

        (bool success, ) = task.client.call{value: refundAmount}("");
        require(success, "Refund transfer failed");

        emit TaskRefunded(taskId, task.client, refundAmount);
    }

    /**
     * @notice Either client or agent can open a dispute if delivery is non-compliant or contested.
     */
    function openDispute(bytes32 taskId, bytes32 evidenceHash) external {
        Task storage task = tasks[taskId];
        require(
            msg.sender == task.client || msg.sender == task.agent,
            "Only client or agent can dispute"
        );
        require(
            task.state == TaskState.IN_PROGRESS || task.state == TaskState.DELIVERED,
            "State not disputable"
        );

        task.state = TaskState.DISPUTED;
        emit TaskDisputed(taskId, msg.sender, evidenceHash);
    }

    /**
     * @notice Appointed human reviewer resolves dispute and distributes escrow.
     */
    function resolveDispute(bytes32 taskId, DisputeOutcome outcome) external onlyReviewer inState(taskId, TaskState.DISPUTED) nonReentrant {
        Task storage task = tasks[taskId];
        uint256 total = task.amount;
        require(total > 0, "No funds to settle");

        task.amount = 0;

        if (outcome == DisputeOutcome.PAY_AGENT) {
            task.state = TaskState.SETTLED;
            (bool success, ) = task.agent.call{value: total}("");
            require(success, "Transfer failed");
        } else if (outcome == DisputeOutcome.REFUND_CLIENT) {
            task.state = TaskState.REFUNDED;
            (bool success, ) = task.client.call{value: total}("");
            require(success, "Transfer failed");
        } else if (outcome == DisputeOutcome.SPLIT_50_50) {
            task.state = TaskState.SETTLED;
            uint256 half = total / 2;
            (bool s1, ) = task.agent.call{value: half}("");
            (bool s2, ) = task.client.call{value: total - half}("");
            require(s1 && s2, "Split transfer failed");
        }

        emit DisputeResolved(taskId, outcome);
    }
}
